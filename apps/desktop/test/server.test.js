const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  allocateLoopbackPort,
  buildServerLaunchPlan,
  redactStartupOutput,
  resolveRuntime,
  startDesktopServer,
  stopServer,
  waitForReadiness,
} = require('../src/server');
const {
  createNativeAffordances,
  isProjectRelativePath,
} = require('../src/native');

function fakeChild() {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.exitCode = null;
  child.killed = false;
  child.killCalls = [];
  child.kill = (signal) => {
    child.killCalls.push(signal);
    child.killed = true;
    child.exitCode = 0;
    queueMicrotask(() => child.emit('exit', 0, signal));
    return true;
  };
  return child;
}

test('desktop server launch plan is loopback-only and uses array arguments without a shell', () => {
  const plan = buildServerLaunchPlan({
    repoRoot: '/workspace/chess-coach',
    runtime: { executable: 'python3', prefixArgs: [] },
    port: 41829,
  });

  assert.deepEqual(plan, {
    command: 'python3',
    args: ['-m', 'chess_coach', 'web', '--host', '127.0.0.1', '--port', '41829'],
    cwd: '/workspace/chess-coach',
    shell: false,
  });
  assert.equal(plan.args.includes('--allow-lan'), false);
  assert.equal(plan.args.includes('--open'), false);
});

test('runtime resolver honours explicit Python then uv, python, and python3', () => {
  assert.deepEqual(resolveRuntime({ env: { CHESS_COACH_PYTHON: '/opt/python' }, commandExists: () => false }), {
    executable: '/opt/python', prefixArgs: [], description: '/opt/python',
  });
  assert.deepEqual(resolveRuntime({ env: {}, commandExists: (command) => command === 'uv' }), {
    executable: 'uv', prefixArgs: ['run', 'python'], description: 'uv run python',
  });
  assert.deepEqual(resolveRuntime({ env: {}, commandExists: (command) => command === 'python' }), {
    executable: 'python', prefixArgs: [], description: 'python',
  });
  assert.deepEqual(resolveRuntime({ env: {}, commandExists: (command) => command === 'python3' }), {
    executable: 'python3', prefixArgs: [], description: 'python3',
  });
});

test('startup output capture redacts token-shaped text before it is retained', () => {
  const output = redactStartupOutput('LICHESS_TOKEN=private-value Authorization: Bearer bearer-value token: another-private-value');

  assert.equal(output.includes('private-value'), false);
  assert.equal(output.includes('bearer-value'), false);
  assert.equal(output.includes('another-private-value'), false);
  assert.match(output, /\[redacted\]/);
});

test('free-port allocator binds Node net to loopback before returning the assigned port', async () => {
  let boundHost = null;
  let closeCalled = false;
  const listeners = new Map();
  const server = {
    once(event, callback) { listeners.set(event, callback); return server; },
    listen({ host }) { boundHost = host; listeners.get('listening')(); },
    address() { return { port: 41829 }; },
    close(callback) { closeCalled = true; callback(); },
  };

  const port = await allocateLoopbackPort({ netModule: { createServer: () => server } });

  assert.equal(boundHost, '127.0.0.1');
  assert.equal(closeCalled, true);
  assert.equal(port, 41829);
});

test('server manager waits for bootstrap readiness before returning the canonical root URL', async () => {
  const child = fakeChild();
  const calls = [];
  const server = await startDesktopServer({
    repoRoot: '/workspace/chess-coach',
    runtime: { executable: 'python3', prefixArgs: [] },
    allocatePort: async () => 41829,
    spawnImpl: (command, args, options) => {
      calls.push({ command, args, options });
      return child;
    },
    fetchImpl: async (url) => ({ ok: url === 'http://127.0.0.1:41829/api/bootstrap' }),
    pollIntervalMs: 0,
  });

  assert.equal(server.url, 'http://127.0.0.1:41829/');
  assert.deepEqual(calls, [{
    command: 'python3',
    args: ['-m', 'chess_coach', 'web', '--host', '127.0.0.1', '--port', '41829'],
    options: { cwd: '/workspace/chess-coach', shell: false, stdio: ['ignore', 'pipe', 'pipe'] },
  }]);
  await server.stop();
});

test('readiness rejects immediately when the server child exits before bootstrap responds', async () => {
  const child = fakeChild();
  const pendingFetch = new Promise(() => {});
  queueMicrotask(() => child.emit('exit', 2, null));

  await assert.rejects(
    waitForReadiness({ child, url: 'http://127.0.0.1:41829/api/bootstrap', fetchImpl: async () => pendingFetch, timeoutMs: 500 }),
    /exited before becoming ready/,
  );
});

test('readiness timeout rejects cleanly when bootstrap never becomes ready', async () => {
  const child = fakeChild();

  await assert.rejects(
    waitForReadiness({ child, url: 'http://127.0.0.1:41829/api/bootstrap', fetchImpl: async () => ({ ok: false }), timeoutMs: 15, pollIntervalMs: 1 }),
    /did not become ready/,
  );
});

test('server stop terminates the child process', async () => {
  const child = fakeChild();

  await stopServer(child, { terminateAfterMs: 20 });

  assert.deepEqual(child.killCalls, ['SIGTERM']);
});

test('native affordances canonicalise existing paths and return only project-relative picker values', async (t) => {
  const temporaryRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'chess-coach-native-'));
  t.after(() => fs.rmSync(temporaryRoot, { recursive: true, force: true }));
  const repoRoot = path.join(temporaryRoot, 'repo');
  const outsideRoot = path.join(temporaryRoot, 'outside');
  fs.mkdirSync(path.join(repoRoot, 'input'), { recursive: true });
  fs.mkdirSync(path.join(repoRoot, 'reports'), { recursive: true });
  fs.mkdirSync(outsideRoot, { recursive: true });
  const localPgn = path.join(repoRoot, 'input', 'games.pgn');
  const localReport = path.join(repoRoot, 'reports', 'latest.md');
  const outsideFile = path.join(outsideRoot, 'outside.md');
  fs.writeFileSync(localPgn, '[Event "Local"]\n', 'utf8');
  fs.writeFileSync(localReport, '# Local report\n', 'utf8');
  fs.writeFileSync(outsideFile, '# Outside\n', 'utf8');
  fs.symlinkSync(outsideFile, path.join(repoRoot, 'reports', 'outside-link.md'));
  fs.symlinkSync(outsideRoot, path.join(repoRoot, 'escape'));

  const calls = [];
  let selectedOpenPath = localPgn;
  let selectedSavePath = path.join(repoRoot, 'reports', 'new-report.md');
  const native = createNativeAffordances({
    repoRoot,
    dialog: {
      showOpenDialog: async () => ({ canceled: false, filePaths: [selectedOpenPath] }),
      showSaveDialog: async () => ({ canceled: false, filePath: selectedSavePath }),
    },
    shell: {
      openPath: async (value) => calls.push(['path', value]),
      openExternal: async (value) => calls.push(['external', value]),
    },
  });

  assert.equal(isProjectRelativePath('reports/latest.md'), true);
  assert.equal(isProjectRelativePath('../outside.md'), false);
  assert.equal(isProjectRelativePath('/tmp/outside.md'), false);
  await native.openPath('reports/latest.md');
  assert.equal(await native.pickPath({ purpose: 'pgnInput' }), path.join('input', 'games.pgn'));
  assert.equal(await native.pickPath({ purpose: 'markdownOutput' }), path.join('reports', 'new-report.md'));

  selectedOpenPath = outsideFile;
  await assert.rejects(async () => native.pickPath({ purpose: 'pgnInput' }), /project-local/);
  selectedSavePath = path.join(repoRoot, 'escape', 'escaped-report.md');
  await assert.rejects(async () => native.pickPath({ purpose: 'markdownOutput' }), /project-local/);
  await assert.rejects(async () => native.openPath('reports/outside-link.md'), /project-local/);
  await native.openExternal('https://lichess.org/study');
  await assert.rejects(async () => native.openPath('../outside.md'), /project-local/);
  await assert.rejects(async () => native.openExternal('http://lichess.org/study'), /allowlist/);
  await assert.rejects(async () => native.openExternal('https://example.com/'), /allowlist/);
  assert.deepEqual(calls, [
    ['path', localReport],
    ['external', 'https://lichess.org/study'],
  ]);
});
