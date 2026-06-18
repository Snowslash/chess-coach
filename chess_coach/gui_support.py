from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen as default_urlopen

from . import __version__
from .config import (
    DEFAULT_CHESS_COACH_OUT,
    DEFAULT_CHESS_COACH_PGN,
    DEFAULT_ENV_FILE,
    REDACTED_SECRET,
    ChessCoachConfig,
    config_as_dict,
    config_from_env_values,
    default_config,
    load_config,
    parse_env_file,
    render_env_file,
    write_env_file,
)
from .maia2_analyser import maia2_available
from .stockfish_analyser import stockfish_available

MAIA_ELO_OPTIONS = (1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900)
MAIA_GAME_TYPE_OPTIONS = ("rapid", "blitz", "bullet", "classical")
MAIA_DEVICE_OPTIONS = ("cpu", "cuda", "mps")
SAFE_LICHESS_USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,28}$")
DIAGNOSTICS_RELATIVE_DIR = Path(".coach") / "diagnostics"



def redact_secret(value: str | None) -> str:
    return REDACTED_SECRET if value else ""



def redact_text(text: str, secrets: list[str] | tuple[str, ...]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, REDACTED_SECRET)
    return redacted



def config_from_payload(payload: Mapping[str, Any]) -> ChessCoachConfig:
    def _string(name: str, default: str | None = None) -> str | None:
        raw = payload.get(name, default)
        if raw is None:
            return None
        value = str(raw).strip()
        return value or None

    return ChessCoachConfig(
        stockfish_path=_string("stockfish_path"),
        stockfish_depth=int(payload.get("stockfish_depth", default_config().stockfish_depth)),
        stockfish_time_limit=float(payload.get("stockfish_time_limit", default_config().stockfish_time_limit)),
        default_player=_string("default_player"),
        maia2_enabled=bool(payload.get("maia2_enabled", False)),
        maia2_game_type=_string("maia2_game_type", default_config().maia2_game_type) or default_config().maia2_game_type,
        maia2_device=_string("maia2_device", default_config().maia2_device) or default_config().maia2_device,
        maia2_target_elo=int(payload.get("maia2_target_elo", default_config().maia2_target_elo)),
        lichess_token=_string("lichess_token"),
        default_pgn=_string("default_pgn", DEFAULT_CHESS_COACH_PGN) or DEFAULT_CHESS_COACH_PGN,
        default_out=_string("default_out", DEFAULT_CHESS_COACH_OUT) or DEFAULT_CHESS_COACH_OUT,
    )



def validate_gui_config(payload: Mapping[str, Any], *, require_username: bool = False) -> dict[str, Any]:
    errors: dict[str, str] = {}
    warnings: dict[str, str] = {}

    username = str(payload.get("default_player", "") or "").strip()
    text_fields = {
        "stockfish_path": payload.get("stockfish_path", ""),
        "default_player": username,
        "lichess_token": payload.get("lichess_token", ""),
        "default_pgn": payload.get("default_pgn", ""),
        "default_out": payload.get("default_out", ""),
        "maia2_game_type": payload.get("maia2_game_type", ""),
        "maia2_device": payload.get("maia2_device", ""),
    }
    for field_name, raw_value in text_fields.items():
        value = str(raw_value or "")
        if "\n" in value or "\r" in value or "\x00" in value:
            errors[field_name] = "Remove line breaks or control characters."
    if require_username and not username:
        errors["default_player"] = "Lichess username is required for import and analysis."
    elif username and not SAFE_LICHESS_USERNAME.fullmatch(username):
        errors["default_player"] = "Use only letters, numbers, underscore or hyphen."

    def _int_field(name: str, minimum: int, maximum: int) -> int | None:
        raw = payload.get(name)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            errors[name] = f"Enter an integer from {minimum} to {maximum}."
            return None
        if not minimum <= value <= maximum:
            errors[name] = f"Enter an integer from {minimum} to {maximum}."
            return None
        return value

    def _float_field(name: str, minimum: float, maximum: float) -> float | None:
        raw = payload.get(name)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            errors[name] = f"Enter a number from {minimum} to {maximum}."
            return None
        if not minimum <= value <= maximum:
            errors[name] = f"Enter a number from {minimum} to {maximum}."
            return None
        return value

    _int_field("stockfish_depth", 1, 30)
    _float_field("stockfish_time_limit", 0.01, 30.0)

    default_pgn = str(payload.get("default_pgn", DEFAULT_CHESS_COACH_PGN) or DEFAULT_CHESS_COACH_PGN)
    default_out = str(payload.get("default_out", DEFAULT_CHESS_COACH_OUT) or DEFAULT_CHESS_COACH_OUT)
    for field_name, field_value in (("default_pgn", default_pgn), ("default_out", default_out)):
        if Path(field_value).is_absolute():
            warnings[field_name] = "Absolute path: valid, but less portable than a project-local path."

    game_type = str(payload.get("maia2_game_type", "") or "").strip()
    if not game_type:
        errors["maia2_game_type"] = f"Choose one of: {', '.join(MAIA_GAME_TYPE_OPTIONS)}."
    elif game_type not in MAIA_GAME_TYPE_OPTIONS:
        errors["maia2_game_type"] = f"Choose one of: {', '.join(MAIA_GAME_TYPE_OPTIONS)}."

    target_elo = payload.get("maia2_target_elo")
    try:
        elo_value = int(target_elo)
    except (TypeError, ValueError):
        errors["maia2_target_elo"] = f"Choose one of: {', '.join(str(item) for item in MAIA_ELO_OPTIONS)}."
    else:
        if elo_value not in MAIA_ELO_OPTIONS:
            errors["maia2_target_elo"] = f"Choose one of: {', '.join(str(item) for item in MAIA_ELO_OPTIONS)}."

    device = str(payload.get("maia2_device", "") or "").strip()
    if device and device not in MAIA_DEVICE_OPTIONS:
        warnings["maia2_device"] = f"Unknown device '{device}'. Standard options are: {', '.join(MAIA_DEVICE_OPTIONS)}."

    return {"ok": not errors, "errors": errors, "warnings": warnings}



def check_stockfish_readiness(config: ChessCoachConfig) -> dict[str, Any]:
    configured = (config.stockfish_path or "").strip()
    if configured:
        candidate = configured
    else:
        candidate = shutil.which("stockfish")

    if not candidate:
        return {
            "status": "not_configured",
            "configured_path": configured or None,
            "candidate_path": None,
            "details": "Stockfish path is not configured.",
        }

    available, resolved = stockfish_available(config)
    candidate_path = resolved or candidate
    if not available:
        return {
            "status": "missing",
            "configured_path": configured or None,
            "candidate_path": candidate_path,
            "details": "Stockfish binary was not found or is not executable.",
        }

    try:
        import chess.engine

        with chess.engine.SimpleEngine.popen_uci(candidate_path) as engine:
            engine.quit()
            engine_name = engine.id.get("name") or "Stockfish"
    except Exception as exc:  # pragma: no cover - defensive runtime probe path
        return {
            "status": "missing",
            "configured_path": configured or None,
            "candidate_path": candidate_path,
            "details": f"Stockfish probe failed: {exc}",
        }

    return {
        "status": "available",
        "configured_path": configured or None,
        "candidate_path": candidate_path,
        "details": engine_name,
    }



def check_maia_readiness(config: ChessCoachConfig) -> dict[str, Any]:
    status = maia2_available(config)
    return {
        "status": "available" if status.available else ("disabled" if not status.enabled else "missing"),
        "enabled": status.enabled,
        "available": status.available,
        "details": status.reason,
    }



def collect_readiness(config: ChessCoachConfig) -> dict[str, Any]:
    return {
        "stockfish": check_stockfish_readiness(config),
        "maia": check_maia_readiness(config),
    }



def probe_lichess_user(username: str, token: str | None = None, *, urlopen=default_urlopen) -> dict[str, Any]:
    cleaned = username.strip()
    if not cleaned:
        return {"ok": False, "status": "invalid", "message": "Lichess username is required."}
    if not SAFE_LICHESS_USERNAME.fullmatch(cleaned):
        return {"ok": False, "status": "invalid", "message": "Lichess username contains unsupported characters."}

    url = f"https://lichess.org/api/user/{quote(cleaned)}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "chess-coach-desktop/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        if exc.code == 404:
            return {"ok": False, "status": "missing", "message": f"Lichess user not found: {cleaned}"}
        if exc.code == 401:
            return {"ok": False, "status": "auth_error", "message": "Lichess rejected the token."}
        if exc.code == 429:
            return {"ok": False, "status": "rate_limited", "message": "Lichess rate limit hit. Try again later."}
        return {"ok": False, "status": "error", "message": f"Lichess HTTP error {exc.code}."}
    except (URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "status": "error", "message": f"Could not reach lichess.org: {exc}"}

    return {
        "ok": True,
        "status": "available",
        "message": f"Found Lichess user {payload.get('username') or cleaned}.",
        "username": payload.get("username") or cleaned,
        "id": payload.get("id") or cleaned.lower(),
        "url": f"https://lichess.org/@/{cleaned}",
        "token_used": bool(token),
    }



def _git_head(project_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None



def _package_status() -> dict[str, bool]:
    return {
        "python_chess": importlib.util.find_spec("chess") is not None,
        "pydantic": importlib.util.find_spec("pydantic") is not None,
        "maia2": importlib.util.find_spec("maia2") is not None,
    }



def _diagnostic_bundle_dir(project_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return project_root / DIAGNOSTICS_RELATIVE_DIR / f"chess-coach-diagnostic-{stamp}"



def create_diagnostic_bundle(
    *,
    project_root: str | Path,
    env_file: str | Path = DEFAULT_ENV_FILE,
    readiness: Mapping[str, Any] | None = None,
    recent_logs: list[str] | None = None,
    electron_context: Mapping[str, Any] | None = None,
    include_pgn: bool = False,
    include_report: bool = False,
    output_dir: str | Path | None = None,
    selected_paths: Mapping[str, str] | None = None,
) -> Path:
    root = Path(project_root)
    env_path = Path(env_file)
    if not env_path.is_absolute():
        env_path = root / env_path
    config = load_config(env_path)
    bundle_dir = Path(output_dir) if output_dir else _diagnostic_bundle_dir(root)
    bundle_dir.mkdir(parents=True, exist_ok=False)

    secrets = [config.lichess_token or ""]
    logs = [redact_text(entry, secrets) for entry in (recent_logs or [])]

    metadata = {
        "app": {
            "name": "Chess Coach",
            "python_package_version": __version__,
            "git_head": _git_head(root),
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "electron": dict(electron_context or {}),
        "package_status": _package_status(),
        "readiness": dict(readiness or {}),
        "config": config_as_dict(config, redact_token=True),
        "paths": {
            "env_file": str(env_path),
            "project_root": str(root),
        },
    }

    (bundle_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (bundle_dir / "redacted_config.env").write_text(render_env_file(config, redact_token=True), encoding="utf-8")
    (bundle_dir / "recent_logs.txt").write_text("\n".join(logs).rstrip() + ("\n" if logs else ""), encoding="utf-8")

    chosen_paths = dict(selected_paths or {})
    pgn_source = chosen_paths.get("pgn") or config.default_pgn
    report_source = chosen_paths.get("report") or config.default_out

    def _project_local_existing_path(candidate: str | None) -> Path | None:
        if not candidate:
            return None
        source = Path(candidate)
        if not source.is_absolute():
            source = root / source
        try:
            source.resolve().relative_to(root.resolve())
        except ValueError:
            return None
        return source if source.exists() else None

    if include_pgn and pgn_source:
        source = _project_local_existing_path(pgn_source)
        if source:
            shutil.copy2(source, bundle_dir / source.name)

    if include_report and report_source:
        report_path = _project_local_existing_path(report_source)
        if report_path:
            shutil.copy2(report_path, bundle_dir / report_path.name)
            json_path = report_path.with_suffix(".json")
            try:
                json_path.resolve().relative_to(root.resolve())
            except ValueError:
                json_path = None
            if json_path and json_path.exists():
                shutil.copy2(json_path, bundle_dir / json_path.name)

    return bundle_dir



def _load_payload_from_stdin() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)



def _json_dump(data: Mapping[str, Any]) -> int:
    print(json.dumps(data, indent=2))
    return 0



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m chess_coach.gui_support")
    sub = parser.add_subparsers(dest="command", required=True)

    read_config_cmd = sub.add_parser("read-config")
    read_config_cmd.add_argument("--env-file", default=DEFAULT_ENV_FILE)

    write_config_cmd = sub.add_parser("write-config")
    write_config_cmd.add_argument("--env-file", default=DEFAULT_ENV_FILE)

    validate_cmd = sub.add_parser("validate-config")
    validate_cmd.add_argument("--require-username", action="store_true")

    render_cmd = sub.add_parser("render-config")
    render_cmd.add_argument("--redact-token", action="store_true")

    preview_cmd = sub.add_parser("preview-config-file")
    preview_cmd.add_argument("--env-file", required=True)

    readiness_cmd = sub.add_parser("test-readiness")
    readiness_cmd.add_argument("--env-file", default=DEFAULT_ENV_FILE)

    lichess_cmd = sub.add_parser("test-lichess")
    lichess_cmd.add_argument("--user", required=True)
    lichess_cmd.add_argument("--token", default=None, help=argparse.SUPPRESS)

    diagnostic_cmd = sub.add_parser("create-diagnostic-bundle")
    diagnostic_cmd.add_argument("--project-root", default=".")
    diagnostic_cmd.add_argument("--env-file", default=DEFAULT_ENV_FILE)

    args = parser.parse_args(argv)

    if args.command == "read-config":
        env_path = Path(args.env_file)
        file_values = parse_env_file(env_path)
        config = config_from_env_values(file_values, use_environment=False)
        return _json_dump(
            {
                "config": config_as_dict(config),
                "env_file": str(env_path),
                "exists": env_path.exists(),
                "validation": validate_gui_config(config_as_dict(config)),
                "options": {
                    "maia_game_types": list(MAIA_GAME_TYPE_OPTIONS),
                    "maia_devices": list(MAIA_DEVICE_OPTIONS),
                    "maia_elo": list(MAIA_ELO_OPTIONS),
                },
            }
        )

    if args.command == "write-config":
        payload = _load_payload_from_stdin()
        config = config_from_payload(payload)
        validation = validate_gui_config(payload)
        if not validation["ok"]:
            return _json_dump({"ok": False, "validation": validation})
        path = write_env_file(config, args.env_file)
        return _json_dump({"ok": True, "path": str(path)})

    if args.command == "validate-config":
        payload = _load_payload_from_stdin()
        return _json_dump(validate_gui_config(payload, require_username=args.require_username))

    if args.command == "render-config":
        payload = _load_payload_from_stdin()
        config = config_from_payload(payload)
        validation = validate_gui_config(payload)
        return _json_dump({"ok": validation["ok"], "validation": validation, "text": render_env_file(config, redact_token=args.redact_token)})

    if args.command == "preview-config-file":
        env_path = Path(args.env_file)
        file_values = parse_env_file(env_path)
        config = config_from_env_values(file_values, use_environment=False)
        config_payload = config_as_dict(config)
        return _json_dump({"exists": env_path.exists(), "config": config_payload, "validation": validate_gui_config(config_payload)})

    if args.command == "test-readiness":
        config = load_config(args.env_file)
        return _json_dump(collect_readiness(config))

    if args.command == "test-lichess":
        payload = _load_payload_from_stdin()
        token = payload.get("token") if isinstance(payload, dict) else None
        return _json_dump(probe_lichess_user(args.user, token=token or args.token))

    if args.command == "create-diagnostic-bundle":
        payload = _load_payload_from_stdin()
        bundle_dir = create_diagnostic_bundle(
            project_root=args.project_root,
            env_file=args.env_file,
            readiness=payload.get("readiness"),
            recent_logs=payload.get("recent_logs"),
            electron_context=payload.get("electron_context"),
            include_pgn=bool(payload.get("include_pgn", False)),
            include_report=bool(payload.get("include_report", False)),
            output_dir=payload.get("output_dir"),
            selected_paths=payload.get("selected_paths"),
        )
        return _json_dump({"ok": True, "path": str(bundle_dir)})

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
