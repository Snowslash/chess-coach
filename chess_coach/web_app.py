from __future__ import annotations

import json
import platform
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .annotated_pgn import count_games_to_export, render_annotated_pgn
from .config import (
    DEFAULT_CHESS_COACH_OUT,
    DEFAULT_CHESS_COACH_PGN,
    DEFAULT_ENV_FILE,
    REDACTED_SECRET,
    config_as_dict,
    default_config,
    load_config,
    write_env_file,
)
from .gui_support import (
    MAIA_DEVICE_OPTIONS,
    MAIA_ELO_OPTIONS,
    MAIA_GAME_TYPE_OPTIONS,
    collect_readiness,
    config_from_payload,
    create_diagnostic_bundle,
    probe_lichess_user,
    redact_text,
    validate_gui_config,
)
from .lichess_import import fetch_recent_games
from .models import AnalysisBundle
from .pipeline import analyse_pgn
from .report_writer import default_json_path

APP_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = APP_DIR / "apps" / "web" / "static"
SAFE_LICHESS_USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,28}$")
DEFAULT_LICHESS_IMPORT_PGN = "input/lichess_recent.pgn"


class ConfigPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stockfish_path: str | None = None
    stockfish_depth: int = 12
    stockfish_time_limit: float = 0.1
    default_player: str | None = None
    maia2_enabled: bool = False
    maia2_game_type: str = "rapid"
    maia2_device: str = "cpu"
    maia2_target_elo: int = 1500
    lichess_token: str | None = None
    default_pgn: str = DEFAULT_CHESS_COACH_PGN
    default_out: str = DEFAULT_CHESS_COACH_OUT


class LichessTestPayload(BaseModel):
    username: str = ""
    token: str | None = None


class ImportLichessPayload(BaseModel):
    username: str = ""
    max_games: int = 20
    perf: str | None = None
    rated_only: bool = False
    since_days: int | None = None
    out_path: str = DEFAULT_LICHESS_IMPORT_PGN


class AnalysePayload(BaseModel):
    username: str = ""
    pgn_path: str = ""
    out_path: str = DEFAULT_CHESS_COACH_OUT
    mock: bool = False


class ExportAnnotatedPayload(BaseModel):
    json_path: str = ""
    out_path: str = "reports/annotated/latest.pgn"
    max_games: int | None = 10
    critical_only: bool = True
    include_all_moves: bool = False


class DiagnosticsPayload(BaseModel):
    include_pgn: bool = False
    include_report: bool = False
    selected_paths: dict[str, str] = Field(default_factory=dict)
    recent_logs: list[str] = Field(default_factory=list)


def static_asset_text(name: str) -> str:
    path = STATIC_DIR / name
    return path.read_text(encoding="utf-8")


@contextmanager
def _pushd(path: Path):
    previous = Path.cwd()
    try:
        path.mkdir(parents=True, exist_ok=True)
        os_chdir = __import__("os").chdir
        os_chdir(path)
        yield
    finally:
        __import__("os").chdir(previous)


def _ensure_project_local(project_root: Path, raw_path: str, *, label: str, must_exist: bool = False) -> Path:
    cleaned = str(raw_path or "").strip()
    if not cleaned:
        raise ValueError(f"{label} is required.")
    candidate = Path(cleaned)
    if candidate.is_absolute():
        raise ValueError(f"{label} must stay inside the Chess Coach project folder in this slice.")
    resolved = (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the Chess Coach project folder in this slice.") from exc
    if must_exist and not resolved.exists():
        raise ValueError(f"{label} not found: {candidate}")
    return candidate


def _serialise_config(env_file: Path) -> dict[str, Any]:
    exists = env_file.exists()
    config = load_config(env_file) if exists else default_config()
    payload = config_as_dict(config)
    payload["lichess_token"] = payload.get("lichess_token") or ""
    return {
        "exists": exists,
        "env_file": str(env_file),
        "config": payload,
        "validation": validate_gui_config(payload),
        "options": {
            "maia_game_types": list(MAIA_GAME_TYPE_OPTIONS),
            "maia_devices": list(MAIA_DEVICE_OPTIONS),
            "maia_elo": list(MAIA_ELO_OPTIONS),
        },
    }


def _default_import_runner(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    username = payload["username"]
    out_path = _ensure_project_local(project_root, payload["out_path"], label="out_path")
    with _pushd(project_root):
        written = fetch_recent_games(
            username,
            out_path,
            max_games=payload["max_games"],
            perf=payload.get("perf") or None,
            rated_only=payload.get("rated_only", False),
            since_days=payload.get("since_days"),
        )
    return {
        "ok": True,
        "out_path": str(written),
        "stdout": f"Imported Lichess PGN: {written}",
        "stderr": "",
    }


def _default_analyse_runner(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    pgn_path = _ensure_project_local(project_root, payload["pgn_path"], label="pgn_path", must_exist=True)
    out_path = _ensure_project_local(project_root, payload["out_path"], label="out_path")
    with _pushd(project_root):
        bundle = analyse_pgn(pgn_path, out_path, player=payload["username"], mock=payload.get("mock", False))
    json_path = default_json_path(out_path)
    return {
        "ok": True,
        "markdown_path": str(out_path),
        "json_path": str(json_path),
        "games_analysed": len(bundle.games),
        "stdout": f"Markdown report: {out_path}\nStructured JSON: {json_path}",
        "stderr": "",
    }


def _default_export_runner(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    json_path = _ensure_project_local(project_root, payload["json_path"], label="json_path", must_exist=True)
    out_path = _ensure_project_local(project_root, payload["out_path"], label="out_path")
    with _pushd(project_root):
        source = (project_root / json_path).read_text(encoding="utf-8")
        bundle = AnalysisBundle.model_validate_json(source)
        rendered = render_annotated_pgn(
            bundle,
            max_games=payload.get("max_games"),
            critical_only=payload.get("critical_only", True),
            include_all_moves=payload.get("include_all_moves", False),
        )
        exported_games = count_games_to_export(bundle, max_games=payload.get("max_games"))
        destination = project_root / out_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    return {
        "ok": True,
        "out_path": str(out_path),
        "games_exported": exported_games,
        "stdout": f"Annotated PGN: {out_path}",
        "stderr": "",
    }


def _validation_error(status_code: int, validation: dict[str, Any]) -> HTTPException:
    return HTTPException(status_code=status_code, detail=validation)


def _raise_with_validation(validation: dict[str, Any], *, status_code: int = 400) -> None:
    if validation["ok"]:
        return
    raise _validation_error(status_code, validation)


def _handle_http_error(exc: HTTPException):
    return {"ok": False, **exc.detail}


def create_app(
    *,
    project_root: str | Path | None = None,
    env_file: str | Path | None = None,
    readiness_collector: Callable[[Any], dict[str, Any]] = collect_readiness,
    lichess_probe: Callable[[str, str | None], dict[str, Any]] = probe_lichess_user,
    workflow_runners: Mapping[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
    diagnostic_bundle_creator: Callable[..., Path] = create_diagnostic_bundle,
) -> FastAPI:
    root = Path(project_root or APP_DIR).resolve()
    env_path = Path(env_file).resolve() if env_file else (root / DEFAULT_ENV_FILE)
    app = FastAPI(title="Chess Coach", version=__version__)
    app.state.project_root = root
    app.state.env_file = env_path
    app.state.default_config = default_config()
    app.state.readiness_collector = readiness_collector
    app.state.lichess_probe = lichess_probe
    app.state.workflow_runners = {
        "import_lichess": lambda payload: _default_import_runner(root, payload),
        "analyse": lambda payload: _default_analyse_runner(root, payload),
        "export_annotated_pgn": lambda payload: _default_export_runner(root, payload),
    }
    if workflow_runners:
        app.state.workflow_runners.update(dict(workflow_runners))
    app.state.diagnostic_bundle_creator = diagnostic_bundle_creator

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    def root_page() -> HTMLResponse:
        return HTMLResponse(static_asset_text("index.html"))

    @app.get("/api/bootstrap")
    def bootstrap() -> dict[str, Any]:
        return {
            "app": {"name": "Chess Coach", "version": __version__},
            "paths": {
                "project_root": str(root),
                "config_path": str(env_path),
                "default_pgn": DEFAULT_CHESS_COACH_PGN,
                "default_out": DEFAULT_CHESS_COACH_OUT,
                "static_dir": str(STATIC_DIR),
            },
            "runtime": {
                "python": sys.version,
                "python_executable": sys.executable,
                "platform": platform.platform(),
            },
            "privacy": {
                "bind_host": "127.0.0.1",
                "local_only": True,
                "telemetry": False,
                "token_boundary": "Lichess tokens are only sent to lichess.org when you explicitly test or use Lichess features.",
                "storage": "Generated PGNs, reports, and diagnostics stay local.",
            },
            "options": {
                "maia_game_types": list(MAIA_GAME_TYPE_OPTIONS),
                "maia_devices": list(MAIA_DEVICE_OPTIONS),
                "maia_elo": list(MAIA_ELO_OPTIONS),
            },
        }

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        return _serialise_config(env_path)

    @app.post("/api/config/validate")
    def validate_config(payload: ConfigPayload) -> dict[str, Any]:
        validation = validate_gui_config(payload.model_dump())
        _raise_with_validation(validation)
        return validation

    @app.post("/api/config")
    def save_config(payload: ConfigPayload) -> dict[str, Any]:
        data = payload.model_dump()
        validation = validate_gui_config(data)
        _raise_with_validation(validation)
        config = config_from_payload(data)
        path = write_env_file(config, env_path)
        return {
            "ok": True,
            "path": str(path),
            "config": config_as_dict(config, redact_token=True),
            "validation": validation,
        }

    @app.get("/api/readiness")
    def readiness() -> dict[str, Any]:
        config = load_config(env_path) if env_path.exists() else default_config()
        return app.state.readiness_collector(config)

    @app.post("/api/lichess/test")
    def test_lichess(payload: LichessTestPayload) -> dict[str, Any]:
        username = payload.username.strip()
        if not username:
            raise _validation_error(400, {"ok": False, "errors": {"username": "Lichess username is required."}})
        result = dict(app.state.lichess_probe(username, payload.token))
        result.pop("token", None)
        return result

    @app.post("/api/import-lichess")
    def import_lichess(payload: ImportLichessPayload) -> dict[str, Any]:
        data = payload.model_dump()
        errors: dict[str, str] = {}
        if not data["username"].strip() or not SAFE_LICHESS_USERNAME.fullmatch(data["username"].strip()):
            errors["username"] = "Use a valid Lichess username."
        if not 1 <= data["max_games"] <= 200:
            errors["max_games"] = "Choose between 1 and 200 games."
        if data.get("since_days") is not None and data["since_days"] < 1:
            errors["since_days"] = "Enter a positive number of days."
        try:
            _ensure_project_local(root, data["out_path"], label="out_path")
        except ValueError as exc:
            errors["out_path"] = str(exc)
        if errors:
            raise _validation_error(400, {"ok": False, "errors": errors})
        return app.state.workflow_runners["import_lichess"](data)

    @app.post("/api/analyse")
    def analyse(payload: AnalysePayload) -> dict[str, Any]:
        data = payload.model_dump()
        errors: dict[str, str] = {}
        username = data["username"].strip()
        if not username or not SAFE_LICHESS_USERNAME.fullmatch(username):
            errors["username"] = "Use a valid Lichess username."
        for field in ("pgn_path", "out_path"):
            try:
                _ensure_project_local(root, data[field], label=field, must_exist=(field == "pgn_path"))
            except ValueError as exc:
                errors[field] = str(exc)
        if errors:
            raise _validation_error(400, {"ok": False, "errors": errors})
        return app.state.workflow_runners["analyse"](data)

    @app.post("/api/export-annotated-pgn")
    def export_annotated_pgn(payload: ExportAnnotatedPayload) -> dict[str, Any]:
        data = payload.model_dump()
        errors: dict[str, str] = {}
        for field in ("json_path", "out_path"):
            try:
                _ensure_project_local(root, data[field], label=field, must_exist=(field == "json_path"))
            except ValueError as exc:
                errors[field] = str(exc)
        max_games = data.get("max_games")
        if max_games is not None and max_games < 1:
            errors["max_games"] = "Choose at least one game to export."
        if errors:
            raise _validation_error(400, {"ok": False, "errors": errors})
        return app.state.workflow_runners["export_annotated_pgn"](data)

    @app.post("/api/diagnostics")
    def diagnostics(payload: DiagnosticsPayload) -> dict[str, Any]:
        selected_paths = {}
        for key, value in payload.selected_paths.items():
            if value:
                _ensure_project_local(root, value, label=key)
                selected_paths[key] = value
        bundle_path = app.state.diagnostic_bundle_creator(
            project_root=root,
            env_file=env_path,
            readiness=readiness(),
            recent_logs=[redact_text(item, [load_config(env_path).lichess_token or ""]) for item in payload.recent_logs],
            include_pgn=payload.include_pgn,
            include_report=payload.include_report,
            selected_paths=selected_paths,
        )
        return {"ok": True, "path": str(bundle_path)}

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request, exc: HTTPException):
        return __import__("fastapi.responses").responses.JSONResponse(status_code=exc.status_code, content=_handle_http_error(exc))

    return app
