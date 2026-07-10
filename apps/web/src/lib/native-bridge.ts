export interface NativeDesktopBridge {
  pickPath?: (payload: { purpose: "pgnInput" | "markdownOutput" | "pgnOutput"; currentValue?: string }) => Promise<string | null>;
  openPath: (projectRelativePath: string) => Promise<void>;
  openExternal?: (allowlistedUrl: string) => Promise<void>;
}

declare global {
  interface Window {
    chessCoachDesktop?: NativeDesktopBridge;
  }
}

export function isProjectRelativePath(value: string): boolean {
  const isWindowsAbsolute = /^[A-Za-z]:/.test(value) && (value[2] === "/" || value[2] === "\\");
  return Boolean(value)
    && !value.startsWith("/")
    && !isWindowsAbsolute
    && !value.split(/[\\/]/).includes("..");
}

export function getNativeBridge(): NativeDesktopBridge | null {
  const bridge = window.chessCoachDesktop;
  return bridge && typeof bridge.openPath === "function" ? bridge : null;
}
