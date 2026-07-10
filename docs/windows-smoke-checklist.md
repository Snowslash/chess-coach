# Windows smoke checklist

Run this only on a real, disposable Windows test environment. Record Windows edition/build, architecture, Python version, Stockfish version, commit, commands, timestamps, screenshots where useful, and exact failures. Do not use private PGNs or a production Lichess token.

## Preconditions

- [ ] Clean Windows user profile with a normal path containing spaces, for example `C:\Users\Test User\`.
- [ ] No WSL dependency.
- [ ] Python 3.11 or newer installed and visible in a new terminal.
- [ ] A non-private committed/sample PGN available.
- [ ] Stockfish installed in a normal Windows location.
- [ ] Maia initially absent.
- [ ] Test credential, if a Lichess probe is explicitly required; never print or record it.

## Python/browser route

- [ ] Install the locally built wheel into an isolated environment.
- [ ] Confirm `python -m chess_coach --help` and the `chess-coach` console script work.
- [ ] Start on the default loopback host and an available port.
- [ ] Confirm the browser opens the React UI at `/`.
- [ ] Confirm `/legacy/` remains available and `/next/` redirects to `/`.
- [ ] Confirm binding is loopback-only with `netstat` or `Get-NetTCPConnection`.
- [ ] Confirm an untrusted `Host` is rejected.
- [ ] Confirm a non-loopback mutation `Origin` is rejected.
- [ ] Save settings, restart, and confirm persistence.
- [ ] Analyse the committed/sample PGN with Stockfish.
- [ ] Verify Markdown and JSON outputs.
- [ ] Export annotated PGN.
- [ ] Create diagnostics with PGN/report inclusion disabled, then enabled only for the non-private fixture.
- [ ] Confirm no token appears in config responses, UI, logs, reports, or diagnostics.
- [ ] Remove the environment/package and confirm no application process or listener remains.

## Optional Maia route

- [ ] Confirm Maia-absent state is clear and does not break Stockfish analysis.
- [ ] If practical, install the documented Maia extra separately.
- [ ] Confirm the model-weight location is local and excluded from source control/package artifacts.
- [ ] Run one non-private fixture analysis and record startup time and additional disk footprint.

## Electron thin shell

Do not perform this section until a Windows Electron package or source launch is deliberately prepared.

- [ ] Start Electron from a path containing spaces.
- [ ] Confirm it resolves Python without invoking a shell string.
- [ ] Confirm it starts FastAPI on a random loopback port and waits for bootstrap.
- [ ] Confirm the same React UI loads; no legacy Electron renderer is used.
- [ ] Confirm `contextIsolation: true`, `nodeIntegration: false`, and sandboxing remain effective.
- [ ] Confirm new windows/navigation are denied outside the local origin.
- [ ] Confirm external URLs are limited to allowlisted HTTPS hosts.
- [ ] Confirm native file picking returns project-relative paths only.
- [ ] Confirm project-local symlinks/junctions cannot open files outside the project.
- [ ] Confirm report, JSON, and annotated PGN native open actions work.
- [ ] Quit and confirm Electron and Python child processes terminate and the port closes.
- [ ] Restart and confirm settings persist.

## Installer decision gate

Choose the browser launcher unless user testing demonstrates that native dialogs/windowing materially improve usability enough to justify Electron plus Python.

Before any release:

- [ ] Compare installer and installed sizes.
- [ ] Record cold and warm startup reliability.
- [ ] Verify install, upgrade, repair, and uninstall.
- [ ] Review licences and notices.
- [ ] Do not bundle Stockfish, Maia/Torch, or model weights without a separate licensing, source-offer, size, and update review.
- [ ] Review signing and update strategy.
- [ ] Repeat the private-artifact and token-redaction audit on the exact release artifact.
