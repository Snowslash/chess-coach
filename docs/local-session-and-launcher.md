# Local session and browser launcher

The loopback FastAPI application creates a random session token for each application instance.
`GET /api/bootstrap` remains public for browser/Electron startup and returns `session_token`
with `Cache-Control: no-store`. Every mutating `/api/` request requires that value in
`X-Chess-Coach-Session`. React (including the Electron thin shell) and `/legacy/` fetch
bootstrap before each mutation. Tokens are not placed in URLs or persistent browser storage.
There is no new business IPC or Electron token store. CLI workflows are unchanged.

Trusted Host and mutation Origin checks remain in place; no CORS permission or LAN exposure
has been added. This is a browser request-forgery boundary, **not authentication against
other local processes**: software that can read loopback bootstrap can obtain the token.
Do not publish this API on a network or call this multi-user authentication. The public
read-only API behavior is retained for compatibility.

## Browser-first packaging

Build the React production bundle first (`cd apps/web; npm ci --include=dev; npm run build`).
Build a wheel/sdist with `python -m build` in a lightweight Python environment. Never use a
Maia/Torch environment to freeze the first launcher. Inspect both archives and the frozen
folder for private inputs, reports, credentials, runtime state, weights and engine binaries.
Stockfish and optional Maia remain separately installed dependencies.

`scripts/run_web_gui.py` is the source/PyInstaller entry point. With no arguments it opens
the browser after Uvicorn is listening. Working data and settings use the launch working
folder, not the frozen application directory. With arguments it accepts the `web` command's
options; explicitly add `--open` if wanted, e.g. `chess-coach-browser --port 5182 --open`.
The server stays in the foreground; Ctrl-C terminates it. This is not an installer, tray
application, signing/update service or a Windows acceptance claim.

Linux development build:

```sh
python -m PyInstaller --noconfirm --onedir --name chess-coach-browser \
  --collect-all chess_coach --collect-submodules uvicorn \
  --exclude-module torch --exclude-module maia2 scripts/run_web_gui.py
```

For a Windows build, use `scripts/build_browser_launcher.ps1` in a Windows venv with
Chess Coach and PyInstaller installed, after the frontend build. Run the complete
`docs/windows-smoke-checklist.md` against that exact artifact. Build/installation, paths
with spaces, browser launch, persistence, engine/report/export, shutdown and uninstall
remain real-Windows gates. The legacy Electron renderer must remain until those pass.
