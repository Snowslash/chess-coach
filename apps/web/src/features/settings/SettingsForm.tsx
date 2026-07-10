import type { ChangeEvent, FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type { ConfigOptions, ReadinessResponse } from "@/lib/api-types";

import type { SettingsValues } from "./settings-schema";

interface SettingsFormProps {
  values: SettingsValues;
  errors: Record<string, string>;
  options: ConfigOptions;
  readiness: ReadinessResponse | null;
  firstRun: boolean;
  tokenConfigured: boolean;
  saving: boolean;
  onChange: (field: keyof SettingsValues, value: string | number | boolean) => void;
  onSubmit: () => void;
  onRefreshReadiness: () => void;
  onClearToken: () => void;
}

function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? <p className="field-error" id={id} role="alert">{message}</p> : null;
}

export function SettingsForm({
  values,
  errors,
  options,
  readiness,
  firstRun,
  tokenConfigured,
  saving,
  onChange,
  onSubmit,
  onRefreshReadiness,
  onClearToken,
}: SettingsFormProps) {
  const usernameError = errors.default_player;
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };
  const textChange = (field: keyof SettingsValues) => (event: ChangeEvent<HTMLInputElement>) => onChange(field, event.target.value);

  return (
    <section className="settings-section" id="settings" aria-labelledby="settings-heading">
      <details className="settings-disclosure">
        <summary>
          <h2 id="settings-heading">Settings</h2>
          <span>Open local engine, account and analysis settings.</span>
        </summary>
        <div className="settings-intro">
          <p>Set up local analysis without exposing your saved Lichess token to this page.</p>
          <Button className="button--secondary" disabled={saving} onClick={onRefreshReadiness}>Run readiness check</Button>
        </div>

      {firstRun ? <p className="first-run-notice">First run: save these local essentials after checking readiness.</p> : null}
      {readiness ? (
        <div className="readiness-guidance" aria-live="polite">
          <strong>Stockfish: {readiness.stockfish.status}</strong>
          <p>{readiness.stockfish.details}</p>
          <strong>Maia: {readiness.maia.status}</strong>
          <p>{readiness.maia.details}</p>
        </div>
      ) : null}

        <form className="settings-form" onSubmit={submit}>
        <div className="settings-grid">
          <div className="field-group">
            <Label htmlFor="default_player">Lichess username</Label>
            <Input aria-describedby={usernameError ? "default_player-error" : undefined} aria-invalid={usernameError ? true : undefined} id="default_player" value={values.default_player} onChange={textChange("default_player")} autoComplete="off" />
            <FieldError id="default_player-error" message={usernameError} />
          </div>

          <div className="field-group">
            <Label htmlFor="stockfish_path">Stockfish path</Label>
            <Input id="stockfish_path" value={values.stockfish_path} onChange={textChange("stockfish_path")} />
            <p className="field-help">Leave blank to use a Stockfish executable available on your local PATH.</p>
            <FieldError id="stockfish_path-error" message={errors.stockfish_path} />
          </div>

          <div className="field-group token-control">
            <Label htmlFor="lichess_token">Replace saved Lichess token</Label>
            <Input id="lichess_token" type="password" value={values.lichess_token} onChange={textChange("lichess_token")} autoComplete="new-password" />
            <p className="field-help">{tokenConfigured ? "A local Lichess token is configured." : "No local Lichess token is configured."} Leave this blank to keep the current saved token.</p>
            {tokenConfigured ? <Button className="button--text" disabled={saving} onClick={onClearToken}>Clear saved token</Button> : null}
          </div>

          <div className="field-group field-group--checkbox">
            <Checkbox id="maia2_enabled" checked={values.maia2_enabled} onChange={(event) => onChange("maia2_enabled", event.target.checked)} />
            <Label htmlFor="maia2_enabled">Enable Maia 2 human-likeness analysis</Label>
          </div>
        </div>

        <details className="advanced-settings">
          <summary>Advanced settings</summary>
          <div className="settings-grid">
            <div className="field-group">
              <Label htmlFor="stockfish_depth">Stockfish depth</Label>
              <Input id="stockfish_depth" type="number" min="1" max="30" value={values.stockfish_depth} onChange={(event) => onChange("stockfish_depth", Number(event.target.value))} />
              <FieldError id="stockfish_depth-error" message={errors.stockfish_depth} />
            </div>
            <div className="field-group">
              <Label htmlFor="stockfish_time_limit">Stockfish time limit</Label>
              <Input id="stockfish_time_limit" type="number" min="0.01" max="30" step="0.01" value={values.stockfish_time_limit} onChange={(event) => onChange("stockfish_time_limit", Number(event.target.value))} />
              <FieldError id="stockfish_time_limit-error" message={errors.stockfish_time_limit} />
            </div>
            <div className="field-group">
              <Label htmlFor="maia2_game_type">Maia game type</Label>
              <Select id="maia2_game_type" value={values.maia2_game_type} onChange={(event) => onChange("maia2_game_type", event.target.value)}>
                {options.maia_game_types.map((option) => <option key={option} value={option}>{option}</option>)}
              </Select>
              <FieldError id="maia2_game_type-error" message={errors.maia2_game_type} />
            </div>
            <div className="field-group">
              <Label htmlFor="maia2_device">Maia device</Label>
              <Select id="maia2_device" value={values.maia2_device} onChange={(event) => onChange("maia2_device", event.target.value)}>
                {options.maia_devices.map((option) => <option key={option} value={option}>{option}</option>)}
              </Select>
              <FieldError id="maia2_device-error" message={errors.maia2_device} />
            </div>
            <div className="field-group">
              <Label htmlFor="maia2_target_elo">Maia target Elo</Label>
              <Select id="maia2_target_elo" value={String(values.maia2_target_elo)} onChange={(event) => onChange("maia2_target_elo", Number(event.target.value))}>
                {options.maia_elo.map((option) => <option key={option} value={option}>{option}</option>)}
              </Select>
              <FieldError id="maia2_target_elo-error" message={errors.maia2_target_elo} />
            </div>
            <div className="field-group">
              <Label htmlFor="default_pgn">Default PGN path</Label>
              <Input id="default_pgn" value={values.default_pgn} onChange={textChange("default_pgn")} />
              <FieldError id="default_pgn-error" message={errors.default_pgn} />
            </div>
            <div className="field-group">
              <Label htmlFor="default_out">Default report path</Label>
              <Input id="default_out" value={values.default_out} onChange={textChange("default_out")} />
              <FieldError id="default_out-error" message={errors.default_out} />
            </div>
          </div>
        </details>

        <div className="settings-actions">
          <Button disabled={saving} type="submit">{saving ? "Saving…" : "Save settings"}</Button>
        </div>
        </form>
      </details>
    </section>
  );
}
