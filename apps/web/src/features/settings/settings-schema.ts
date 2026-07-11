import type { ConfigSavePayload, ConfigValues } from "@/lib/api-types";

export interface SettingsValues extends Omit<ConfigSavePayload, "clear_lichess_token"> {}

export const DEFAULT_SETTINGS: SettingsValues = {
  stockfish_path: "",
  stockfish_depth: 12,
  stockfish_time_limit: 0.1,
  default_player: "",
  maia2_enabled: false,
  maia2_game_type: "rapid",
  maia2_device: "cpu",
  maia2_target_elo: 1500,
  lichess_token: "",
  default_pgn: "input/sample_games.pgn",
  default_out: "reports/latest.md",
};

export function settingsFromConfig(config: ConfigValues): SettingsValues {
  return {
    stockfish_path: config.stockfish_path ?? "",
    stockfish_depth: config.stockfish_depth,
    stockfish_time_limit: config.stockfish_time_limit,
    default_player: config.default_player ?? "",
    maia2_enabled: config.maia2_enabled,
    maia2_game_type: config.maia2_game_type,
    maia2_device: config.maia2_device,
    maia2_target_elo: config.maia2_target_elo,
    lichess_token: "",
    default_pgn: config.default_pgn,
    default_out: config.default_out,
  };
}
