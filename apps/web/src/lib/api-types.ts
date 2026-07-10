export interface BootstrapResponse {
  app: {
    name: string;
    version: string;
  };
  privacy: {
    bind_host?: string;
    local_only: boolean;
    telemetry?: boolean;
    storage?: string;
    token_boundary?: string;
  };
}

export interface ReadinessItem {
  status: string;
  details: string;
  available?: boolean;
}

export interface ReadinessResponse {
  stockfish: ReadinessItem;
  maia: ReadinessItem;
}

export interface ConfigValues {
  stockfish_path: string | null;
  stockfish_depth: number;
  stockfish_time_limit: number;
  default_player: string | null;
  maia2_enabled: boolean;
  maia2_game_type: string;
  maia2_device: string;
  maia2_target_elo: number;
  lichess_token: "";
  lichess_token_configured?: boolean;
  default_pgn: string;
  default_out: string;
}

export interface ConfigOptions {
  maia_game_types: string[];
  maia_devices: string[];
  maia_elo: number[];
}

export interface ValidationResponse {
  ok: boolean;
  errors: Record<string, string>;
  warnings: Record<string, string>;
}

export interface ConfigResponse {
  exists: boolean;
  env_file: string;
  config: ConfigValues;
  lichess_token_configured: boolean;
  validation: ValidationResponse;
  options: ConfigOptions;
}

export interface ConfigSavePayload {
  stockfish_path: string;
  stockfish_depth: number;
  stockfish_time_limit: number;
  default_player: string;
  maia2_enabled: boolean;
  maia2_game_type: string;
  maia2_device: string;
  maia2_target_elo: number;
  lichess_token: string;
  clear_lichess_token?: boolean;
  default_pgn: string;
  default_out: string;
}

export interface ConfigSaveResponse {
  ok: true;
  path: string;
  config: ConfigValues;
  lichess_token_configured: boolean;
  validation: ValidationResponse;
}

export interface LichessTestPayload {
  username: string;
  token: string;
}

export interface LichessTestResponse {
  ok: boolean;
  status: string;
  message: string;
  username?: string;
  token_used?: boolean;
}

export interface ImportLichessPayload {
  username: string;
  max_games: number;
  perf: string | null;
  rated_only: boolean;
  since_days: number | null;
  out_path: string;
}

export interface ImportLichessResponse {
  ok: boolean;
  out_path: string;
  stdout: string;
  stderr: string;
}

export interface AnalysePayload {
  username: string;
  pgn_path: string;
  out_path: string;
  mock: boolean;
}

export interface AnalyseResponse {
  ok: boolean;
  markdown_path: string;
  json_path: string;
  games_analysed: number;
  stdout: string;
  stderr: string;
}

export interface ExportAnnotatedPgnPayload {
  json_path: string;
  out_path: string;
  max_games: number | null;
  critical_only: boolean;
  include_all_moves: boolean;
}

export interface ExportAnnotatedPgnResponse {
  ok: boolean;
  out_path: string;
  games_exported: number;
  stdout: string;
  stderr: string;
}

export interface DiagnosticsPayload {
  include_pgn: boolean;
  include_report: boolean;
  selected_paths: Record<string, string>;
  recent_logs: string[];
}

export interface DiagnosticsResponse {
  ok: boolean;
  path: string;
}
