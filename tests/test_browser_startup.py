"""SYNTHETIC server readiness ordering; no actual browser is launched."""
from threading import Event
from chess_coach import web_server


def test_open_browser_waits_until_server_is_listening(monkeypatch, tmp_path):
    import uvicorn
    opened = Event()
    class Server:
        started = False
        def __init__(self, config):
            pass
        def run(self):
            assert not opened.is_set()
            self.started = True
            assert opened.wait(2)
    monkeypatch.setattr(uvicorn, "Server", Server)
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: Server(None).run())
    monkeypatch.setattr(web_server, "open_browser_at", lambda url: opened.set())
    assert web_server.run_web_server(open_browser=True, project_root=tmp_path) == 0
    assert opened.is_set()
