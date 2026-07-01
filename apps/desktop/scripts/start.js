const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const electronBinary = require('electron');
const appPath = path.join(__dirname, '..', 'src', 'main.js');
const chromeSandboxPath = path.join(path.dirname(electronBinary), 'chrome-sandbox');

function hasGraphicalDisplay(env = process.env) {
  return Boolean(String(env.DISPLAY || '').trim() || String(env.WAYLAND_DISPLAY || '').trim());
}

function statOrNull(filePath) {
  try {
    return fs.statSync(filePath);
  } catch {
    return null;
  }
}

function needsNoSandbox({ platform = process.platform, chromeSandboxStat = statOrNull(chromeSandboxPath) } = {}) {
  if (platform !== 'linux' || !chromeSandboxStat) {
    return false;
  }
  const mode = chromeSandboxStat.mode & 0o7777;
  const hasAnyExecuteBit = (mode & 0o111) !== 0;
  const hasSetuidBit = (mode & 0o4000) === 0o4000;
  return hasAnyExecuteBit && (chromeSandboxStat.uid !== 0 || !hasSetuidBit);
}

function buildLaunchPlan({
  platform = process.platform,
  env = process.env,
  electronPath = electronBinary,
  guiAppPath = appPath,
  chromeSandboxStat = statOrNull(chromeSandboxPath),
} = {}) {
  const args = [];
  const errors = [];
  const warnings = [];

  if (needsNoSandbox({ platform, chromeSandboxStat })) {
    args.push('--no-sandbox');
    warnings.push(
      'Electron chrome-sandbox is not root-owned setuid 4755 here; falling back to --no-sandbox for this local launch only.'
    );
  }

  if (platform === 'linux' && !hasGraphicalDisplay(env)) {
    errors.push(
      'No graphical display detected (DISPLAY/WAYLAND_DISPLAY unset). Run Chess Coach from a graphical desktop session on Delphi.'
    );
  }

  args.push(guiAppPath);
  return { command: electronPath, args, errors, warnings };
}

function main() {
  const plan = buildLaunchPlan();
  for (const warning of plan.warnings) {
    console.error(`Warning: ${warning}`);
  }
  if (plan.errors.length > 0) {
    for (const error of plan.errors) {
      console.error(`Error: ${error}`);
    }
    process.exit(2);
  }

  const child = spawn(plan.command, plan.args, {
    stdio: 'inherit',
    shell: false,
  });
  child.on('error', (error) => {
    console.error(`Error: failed to launch Electron: ${error.message}`);
    process.exit(1);
  });
  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 1);
  });
}

module.exports = {
  buildLaunchPlan,
  hasGraphicalDisplay,
  needsNoSandbox,
};

if (require.main === module) {
  main();
}
