const net = require('node:net');
const { spawn, spawnSync } = require('node:child_process');

const LOOPBACK_HOST = '127.0.0.1';
const READINESS_TIMEOUT_MS = 10_000;
const POLL_INTERVAL_MS = 100;
const STARTUP_OUTPUT_LIMIT = 4_096;

function commandExists(command, { cwd, spawnSyncImpl = spawnSync } = {}) {
  const probe = spawnSyncImpl(command, ['--version'], { cwd, stdio: 'ignore', shell: false });
  return probe.status === 0;
}

function resolveRuntime({ env = process.env, cwd, commandExists: hasCommand = (command) => commandExists(command, { cwd }) } = {}) {
  const explicitPython = String(env.CHESS_COACH_PYTHON || '').trim();
  if (explicitPython) {
    return { executable: explicitPython, prefixArgs: [], description: explicitPython };
  }
  if (hasCommand('uv')) {
    return { executable: 'uv', prefixArgs: ['run', 'python'], description: 'uv run python' };
  }
  if (hasCommand('python')) {
    return { executable: 'python', prefixArgs: [], description: 'python' };
  }
  return { executable: 'python3', prefixArgs: [], description: 'python3' };
}

function allocateLoopbackPort({ netModule = net } = {}) {
  return new Promise((resolve, reject) => {
    const server = netModule.createServer();
    server.once('error', reject);
    server.once('listening', () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : null;
      server.close((error) => {
        if (error) {
          reject(error);
        } else if (typeof port === 'number') {
          resolve(port);
        } else {
          reject(new Error('Could not allocate a loopback port.'));
        }
      });
    });
    server.listen({ host: LOOPBACK_HOST, port: 0 });
  });
}

function buildServerLaunchPlan({ repoRoot, runtime, port }) {
  return {
    command: runtime.executable,
    args: [...runtime.prefixArgs, '-m', 'chess_coach', 'web', '--host', LOOPBACK_HOST, '--port', String(port)],
    cwd: repoRoot,
    shell: false,
  };
}

function redactStartupOutput(chunk) {
  return String(chunk)
    .replace(/(LICHESS_TOKEN\s*=\s*)\S+/gi, '$1[redacted]')
    .replace(/(Authorization:\s*Bearer\s+)\S+/gi, '$1[redacted]')
    .replace(/(token\s*[:=]\s*)\S+/gi, '$1[redacted]');
}

function boundedStartupOutput(child) {
  let output = '';
  const append = (chunk) => {
    output = `${output}${redactStartupOutput(chunk)}`.slice(-STARTUP_OUTPUT_LIMIT);
  };
  child.stdout?.on('data', append);
  child.stderr?.on('data', append);
  return () => output.length;
}

function childExitError(code, signal) {
  return new Error(`Chess Coach server exited before becoming ready (${signal || code || 'unknown'}).`);
}

async function waitForReadiness({
  child,
  url,
  fetchImpl = globalThis.fetch,
  timeoutMs = READINESS_TIMEOUT_MS,
  pollIntervalMs = POLL_INTERVAL_MS,
  sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
} = {}) {
  if (typeof fetchImpl !== 'function') {
    throw new Error('No HTTP client is available to verify Chess Coach server readiness.');
  }
  let rejectChildExit;
  const childExited = new Promise((_, reject) => { rejectChildExit = reject; });
  childExited.catch(() => {});
  const onExit = (code, signal) => rejectChildExit(childExitError(code, signal));
  const onError = () => rejectChildExit(new Error('Chess Coach server could not be started.'));
  child.once('exit', onExit);
  child.once('error', onError);
  const deadline = Date.now() + timeoutMs;

  try {
    while (Date.now() <= deadline) {
      const controller = new AbortController();
      const requestTimeout = setTimeout(() => controller.abort(), Math.min(1_000, Math.max(1, timeoutMs)));
      try {
        const response = await Promise.race([
          fetchImpl(url, { signal: controller.signal }),
          childExited,
        ]);
        if (response.ok) {
          return url;
        }
      } catch (error) {
        if (error.message?.includes('exited before becoming ready') || error.message === 'Chess Coach server could not be started.') {
          throw error;
        }
      } finally {
        clearTimeout(requestTimeout);
      }
      if (Date.now() <= deadline) {
        await Promise.race([sleep(pollIntervalMs), childExited]);
      }
    }
  } finally {
    child.removeListener('exit', onExit);
    child.removeListener('error', onError);
  }
  throw new Error('Chess Coach server did not become ready before the startup timeout.');
}

function stopServer(child, { terminateAfterMs = 2_000 } = {}) {
  if (!child || child.exitCode !== null) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    let finished = false;
    const finish = () => {
      if (!finished) {
        finished = true;
        clearTimeout(escalation);
        resolve();
      }
    };
    const escalation = setTimeout(() => {
      child.kill('SIGKILL');
      setTimeout(finish, terminateAfterMs);
    }, terminateAfterMs);
    child.once('exit', finish);
    child.kill('SIGTERM');
  });
}

async function startDesktopServer({
  repoRoot,
  runtime = resolveRuntime({ cwd: repoRoot }),
  allocatePort = allocateLoopbackPort,
  spawnImpl = spawn,
  fetchImpl = globalThis.fetch,
  readinessTimeoutMs = READINESS_TIMEOUT_MS,
  pollIntervalMs = POLL_INTERVAL_MS,
} = {}) {
  const port = await allocatePort();
  const plan = buildServerLaunchPlan({ repoRoot, runtime, port });
  const child = spawnImpl(plan.command, plan.args, {
    cwd: plan.cwd,
    shell: plan.shell,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.on('error', () => {});
  boundedStartupOutput(child);
  const url = `http://${LOOPBACK_HOST}:${port}/`;

  try {
    await waitForReadiness({
      child,
      url: `${url}api/bootstrap`,
      fetchImpl,
      timeoutMs: readinessTimeoutMs,
      pollIntervalMs,
    });
  } catch (error) {
    await stopServer(child);
    throw error;
  }

  return { child, port, url, stop: () => stopServer(child) };
}

module.exports = {
  LOOPBACK_HOST,
  allocateLoopbackPort,
  buildServerLaunchPlan,
  redactStartupOutput,
  resolveRuntime,
  startDesktopServer,
  stopServer,
  waitForReadiness,
};
