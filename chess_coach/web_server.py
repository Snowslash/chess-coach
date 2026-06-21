from __future__ import annotations

import ipaddress
import webbrowser
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def guard_host(host: str, *, allow_lan: bool = False) -> str:
    cleaned = (host or DEFAULT_HOST).strip()
    if cleaned == "localhost":
        return cleaned
    try:
        ip = ipaddress.ip_address(cleaned)
    except ValueError as exc:
        raise ValueError(f"Invalid host: {host}") from exc
    if not ip.is_loopback and not allow_lan:
        raise ValueError("Refusing non-loopback host without --allow-lan. Use 127.0.0.1 or localhost for local-only mode.")
    return cleaned


def parse_host_port(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> tuple[str, int]:
    return host, int(port)


def open_browser_at(url: str) -> bool:
    return webbrowser.open(url)


def run_web_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    open_browser: bool = False,
    allow_lan: bool = False,
    project_root: str | Path | None = None,
    env_file: str | Path | None = None,
) -> int:
    import uvicorn

    from .web_app import create_app

    safe_host = guard_host(host, allow_lan=allow_lan)
    app = create_app(project_root=project_root, env_file=env_file)
    url = f"http://{safe_host}:{port}/"
    print(f"Chess Coach web GUI: {url}")
    if open_browser:
        open_browser_at(url)
    uvicorn.run(app, host=safe_host, port=port, log_level="info")
    return 0
