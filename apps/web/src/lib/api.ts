import type {
  AnalysePayload,
  AnalyseResponse,
  BootstrapResponse,
  ConfigResponse,
  ConfigSavePayload,
  ConfigSaveResponse,
  DiagnosticsPayload,
  DiagnosticsResponse,
  ExportAnnotatedPgnPayload,
  ExportAnnotatedPgnResponse,
  ImportLichessPayload,
  ImportLichessResponse,
  LichessTestPayload,
  LichessTestResponse,
  ReadinessResponse,
} from "./api-types";

export class ApiError extends Error {
  readonly status?: number;
  readonly errors: Record<string, string>;

  constructor(message: string, status?: number, errors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

interface RequestOptions {
  signal?: AbortSignal;
  method?: "GET" | "POST";
  body?: unknown;
}

const SAFE_VALIDATION_ERROR_FIELDS = new Set([
  "stockfish_path",
  "stockfish_depth",
  "stockfish_time_limit",
  "default_player",
  "maia2_enabled",
  "maia2_game_type",
  "maia2_device",
  "maia2_target_elo",
  "default_pgn",
  "default_out",
  "username",
  "max_games",
  "perf",
  "since_days",
  "out_path",
  "pgn_path",
  "json_path",
  "selected_paths",
]);

function safeValidationErrors(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  const response = value as Record<string, unknown>;
  const detail = response.detail;
  const envelope = detail && typeof detail === "object" && !Array.isArray(detail)
    ? detail as Record<string, unknown>
    : response;
  const errors = envelope.errors;
  if (!errors || typeof errors !== "object" || Array.isArray(errors)) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(errors).filter(([field, message]) => SAFE_VALIDATION_ERROR_FIELDS.has(field) && typeof message === "string"),
  );
}

async function requestJson<T>(path: `/api/${string}`, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method ?? "GET",
      headers: options.body === undefined ? undefined : { "Content-Type": "application/json" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch {
    throw new ApiError("Network request failed.");
  }

  if (!response.ok) {
    let errors: Record<string, string> = {};
    try {
      errors = safeValidationErrors(await response.json());
    } catch {
      // The browser never surfaces arbitrary error bodies because they can contain sensitive input.
    }
    throw new ApiError(`Request failed (${response.status}).`, response.status, errors);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("API returned invalid JSON.", response.status);
  }
}

export function getBootstrap(options?: RequestOptions): Promise<BootstrapResponse> {
  return requestJson("/api/bootstrap", options);
}

export function getReadiness(options?: RequestOptions): Promise<ReadinessResponse> {
  return requestJson("/api/readiness", options);
}

export function getConfig(options?: RequestOptions): Promise<ConfigResponse> {
  return requestJson("/api/config", options);
}

export function saveConfig(payload: ConfigSavePayload): Promise<ConfigSaveResponse> {
  return requestJson("/api/config", { method: "POST", body: payload });
}

export function testLichess(payload: LichessTestPayload): Promise<LichessTestResponse> {
  return requestJson("/api/lichess/test", { method: "POST", body: payload });
}

export function importLichess(payload: ImportLichessPayload): Promise<ImportLichessResponse> {
  return requestJson("/api/import-lichess", { method: "POST", body: payload });
}

export function analysePgn(payload: AnalysePayload): Promise<AnalyseResponse> {
  return requestJson("/api/analyse", { method: "POST", body: payload });
}

export function exportAnnotatedPgn(payload: ExportAnnotatedPgnPayload): Promise<ExportAnnotatedPgnResponse> {
  return requestJson("/api/export-annotated-pgn", { method: "POST", body: payload });
}

export function createDiagnostics(payload: DiagnosticsPayload): Promise<DiagnosticsResponse> {
  return requestJson("/api/diagnostics", { method: "POST", body: payload });
}
