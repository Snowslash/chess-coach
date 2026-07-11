import { useCallback, useEffect, useState } from "react";

import { ApiError, getConfig, getReadiness, saveConfig } from "@/lib/api";
import type { ConfigOptions, ReadinessResponse } from "@/lib/api-types";

import { SettingsForm } from "./SettingsForm";
import { DEFAULT_SETTINGS, settingsFromConfig, type SettingsValues } from "./settings-schema";

const EMPTY_OPTIONS: ConfigOptions = {
  maia_game_types: ["rapid"],
  maia_devices: ["cpu"],
  maia_elo: [1500],
};

export function SettingsPage() {
  const [values, setValues] = useState<SettingsValues>(DEFAULT_SETTINGS);
  const [options, setOptions] = useState<ConfigOptions>(EMPTY_OPTIONS);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [firstRun, setFirstRun] = useState(false);
  const [tokenConfigured, setTokenConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");

  const refreshReadiness = useCallback(async () => {
    try {
      setReadiness(await getReadiness());
    } catch {
      setStatus("Readiness check could not complete. Try again after checking local setup.");
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setStatus("");
    try {
      const [config, nextReadiness] = await Promise.all([getConfig(), getReadiness()]);
      setValues(settingsFromConfig(config.config));
      setOptions(config.options);
      setErrors(config.validation.errors);
      setFirstRun(!config.exists);
      setTokenConfigured(config.lichess_token_configured);
      setReadiness(nextReadiness);
    } catch {
      setStatus("Local settings could not load. Check that the Chess Coach server is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const updateValue = (field: keyof SettingsValues, value: string | number | boolean) => {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => {
      const { [field]: _resolved, ...remaining } = current;
      return remaining;
    });
  };

  const persist = async (clearToken = false) => {
    setSaving(true);
    setStatus("");
    try {
      const response = await saveConfig({
        ...values,
        lichess_token: clearToken ? "" : values.lichess_token,
        clear_lichess_token: clearToken || undefined,
      });
      setValues(settingsFromConfig(response.config));
      setErrors(response.validation.errors);
      setTokenConfigured(response.lichess_token_configured);
      setFirstRun(false);
      setStatus(clearToken ? "Saved token removed locally." : "Settings saved locally.");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors(error.errors);
      }
      setStatus("Settings were not saved. Fix the highlighted fields and try again.");
    } finally {
      setSaving(false);
    }
  };

  const clearToken = () => {
    if (window.confirm("Remove the saved local Lichess token? This cannot be undone.")) {
      void persist(true);
    }
  };

  if (loading) {
    return <section className="settings-section"><p>Loading local settings…</p></section>;
  }

  return (
    <>
      <SettingsForm
        errors={errors}
        firstRun={firstRun}
        onChange={updateValue}
        onClearToken={clearToken}
        onRefreshReadiness={() => void refreshReadiness()}
        onSubmit={() => void persist()}
        options={options}
        readiness={readiness}
        saving={saving}
        tokenConfigured={tokenConfigured}
        values={values}
      />
      {status ? <p className="settings-status" role="status">{status}</p> : null}
    </>
  );
}
