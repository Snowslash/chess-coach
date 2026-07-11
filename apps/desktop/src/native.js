const path = require('node:path');
const fs = require('node:fs');

const ALLOWED_EXTERNAL_HOSTS = new Set(['lichess.org', 'stockfishchess.org']);
const PICKER_OPTIONS = {
  pgnInput: { kind: 'open', filters: [{ name: 'PGN files', extensions: ['pgn'] }] },
  markdownOutput: { kind: 'save', filters: [{ name: 'Markdown', extensions: ['md'] }] },
  pgnOutput: { kind: 'save', filters: [{ name: 'PGN files', extensions: ['pgn'] }] },
};

function isProjectRelativePath(target) {
  const isWindowsAbsolute = typeof target === 'string' && /^[A-Za-z]:/.test(target) && (target[2] === '/' || target[2] === '\\');
  if (typeof target !== 'string' || !target.trim() || path.isAbsolute(target) || isWindowsAbsolute) {
    return false;
  }
  const normalised = path.normalize(target);
  return normalised !== '..' && !normalised.startsWith(`..${path.sep}`);
}

function isInsideCanonicalRoot(canonicalRoot, canonicalTarget) {
  const relative = path.relative(canonicalRoot, canonicalTarget);
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

function projectLocalError() {
  return new Error('Only project-local paths can be opened from Chess Coach.');
}

function normaliseRepoPath(repoRoot, target) {
  if (!isProjectRelativePath(target)) {
    throw projectLocalError();
  }
  try {
    const canonicalRoot = fs.realpathSync(repoRoot);
    const canonicalTarget = fs.realpathSync(path.resolve(repoRoot, target));
    if (!isInsideCanonicalRoot(canonicalRoot, canonicalTarget)) {
      throw projectLocalError();
    }
    return canonicalTarget;
  } catch (error) {
    if (error?.message === 'Only project-local paths can be opened from Chess Coach.') {
      throw error;
    }
    throw projectLocalError();
  }
}

function projectRelativePickerPath(repoRoot, selectedPath, { mustExist }) {
  try {
    const lexicalRoot = path.resolve(repoRoot);
    const canonicalRoot = fs.realpathSync(lexicalRoot);
    const lexicalTarget = path.resolve(selectedPath);
    const projectRelative = path.relative(lexicalRoot, lexicalTarget);
    if (!projectRelative || projectRelative === '..' || projectRelative.startsWith(`..${path.sep}`) || path.isAbsolute(projectRelative)) {
      throw projectLocalError();
    }

    if (mustExist || fs.existsSync(lexicalTarget)) {
      const canonicalTarget = fs.realpathSync(lexicalTarget);
      if (!isInsideCanonicalRoot(canonicalRoot, canonicalTarget)) {
        throw projectLocalError();
      }
    } else {
      let existingParent = path.dirname(lexicalTarget);
      while (!fs.existsSync(existingParent)) {
        const parent = path.dirname(existingParent);
        if (parent === existingParent) {
          throw projectLocalError();
        }
        existingParent = parent;
      }
      const canonicalParent = fs.realpathSync(existingParent);
      if (canonicalParent !== canonicalRoot && !isInsideCanonicalRoot(canonicalRoot, canonicalParent)) {
        throw projectLocalError();
      }
    }
    return projectRelative;
  } catch (error) {
    if (error?.message === 'Only project-local paths can be opened from Chess Coach.') {
      throw error;
    }
    throw projectLocalError();
  }
}

function assertAllowedExternalUrl(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new Error('Invalid external URL.');
  }
  if (parsed.protocol !== 'https:' || !ALLOWED_EXTERNAL_HOSTS.has(parsed.hostname)) {
    throw new Error('External link blocked by Chess Coach allowlist.');
  }
  return parsed.toString();
}

function createNativeAffordances({ repoRoot, dialog, shell }) {
  return {
    async pickPath(payload = {}) {
      const option = PICKER_OPTIONS[payload.purpose];
      if (!option) {
        throw new Error('Unsupported file picker request.');
      }
      const defaultPath = isProjectRelativePath(payload.currentValue) ? path.join(repoRoot, payload.currentValue) : repoRoot;
      const settings = { defaultPath, filters: option.filters };
      if (option.kind === 'open') {
        const result = await dialog.showOpenDialog({ ...settings, properties: ['openFile'] });
        if (result.canceled || !result.filePaths[0]) {
          return null;
        }
        return projectRelativePickerPath(repoRoot, result.filePaths[0], { mustExist: true });
      }
      const result = await dialog.showSaveDialog(settings);
      if (result.canceled || !result.filePath) {
        return null;
      }
      return projectRelativePickerPath(repoRoot, result.filePath, { mustExist: false });
    },
    openPath(target) {
      return shell.openPath(normaliseRepoPath(repoRoot, target));
    },
    openExternal(rawUrl) {
      return shell.openExternal(assertAllowedExternalUrl(rawUrl));
    },
  };
}

module.exports = {
  ALLOWED_EXTERNAL_HOSTS,
  assertAllowedExternalUrl,
  createNativeAffordances,
  isProjectRelativePath,
  normaliseRepoPath,
  projectRelativePickerPath,
};
