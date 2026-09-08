"""SYNTHETIC browser-free regression for the retained legacy API transport."""
import subprocess
from pathlib import Path


def test_legacy_mutations_bootstrap_session():
    source = Path("chess_coach/legacy_static/app.js").read_text()
    api = source[source.index("async function api("):source.index("async function loadBootstrap(")]
    script = """
const assert = require('node:assert/strict');
const calls = [];
async function fetch(path, options) {
  calls.push([path, options]);
  return {ok: true, json: async () => path === '/api/bootstrap' ? {session_token: 'SYNTHETIC-session'} : {ok: true}};
}
""" + api + """
(async () => {
  await api('/api/config', {method: 'POST', body: '{}'});
  assert.equal(calls[0][0], '/api/bootstrap');
  assert.equal(calls[1][1].headers['X-Chess-Coach-Session'], 'SYNTHETIC-session');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
