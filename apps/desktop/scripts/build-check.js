const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const mainFile = path.join(root, 'src', 'main.js');
const nativeFile = path.join(root, 'src', 'native.js');
const preloadFile = path.join(root, 'src', 'preload.js');
const rendererAppFile = path.join(root, 'src', 'renderer', 'app.js');
const serverFile = path.join(root, 'src', 'server.js');
const startFile = path.join(root, 'scripts', 'start.js');

for (const file of [mainFile, nativeFile, preloadFile, rendererAppFile, serverFile, startFile]) {
  if (!fs.existsSync(file)) {
    throw new Error(`Missing expected file: ${file}`);
  }
  new Function(fs.readFileSync(file, 'utf-8'));
}

const mainText = fs.readFileSync(mainFile, 'utf-8');
if (!mainText.includes("path.resolve(__dirname, '../../..')")) {
  throw new Error('main.js must resolve the repository root from apps/desktop/src back to the project root.');
}

const rendererText = fs.readFileSync(rendererAppFile, 'utf-8');
if (rendererText.includes('row.innerHTML = `<strong>${label}</strong><div>${value}</div>`')) {
  throw new Error('renderer output paths must be rendered with textContent, not innerHTML.');
}

console.log('Desktop build check passed.');
