import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SettingsPage } from "./SettingsPage";

const configResponse = {
  exists: false,
  config: {
    default_player: "ExampleUser",
    lichess_token: "",
    stockfish_path: "",
    stockfish_depth: 12,
    stockfish_time_limit: 0.5,
    maia2_enabled: false,
    maia2_game_type: "rapid",
    maia2_device: "cpu",
    maia2_target_elo: 1500,
    default_pgn: "input/example.pgn",
    default_out: "reports/example.md",
  },
  lichess_token_configured: true,
  validation: { ok: true, errors: {}, warnings: {} },
  options: { maia_game_types: ["rapid", "blitz"], maia_devices: ["cpu"], maia_elo: [1500, 1600] },
};

const readinessResponse = {
  stockfish: { status: "not_configured", details: "Stockfish path is not configured." },
  maia: { status: "disabled", details: "Not enabled" },
};

function stubSettingsFetch(saveResponse: Response = new Response(JSON.stringify({ ok: true, config: configResponse.config, lichess_token_configured: true, validation: configResponse.validation }))) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input) === "/api/config" && init?.method === "POST") {
      return Promise.resolve(saveResponse);
    }
    if (String(input) === "/api/config") {
      return Promise.resolve(new Response(JSON.stringify(configResponse)));
    }
    return Promise.resolve(new Response(JSON.stringify(readinessResponse)));
  });
}

describe("SettingsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads first-run settings without exposing the configured token and shows readiness guidance", async () => {
    vi.stubGlobal("fetch", stubSettingsFetch());

    render(<SettingsPage />);

    expect(screen.getByText("Loading local settings…")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 2, name: "Settings" })).toBeInTheDocument();
    expect(screen.getByLabelText("Lichess username")).toHaveValue("ExampleUser");
    expect(screen.getByLabelText("Replace saved Lichess token")).toHaveValue("");
    expect(screen.getByText(/A local Lichess token is configured/)).toBeInTheDocument();
    expect(screen.getByText("Stockfish path is not configured.")).toBeInTheDocument();
    expect(screen.getByText(/First run/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run readiness check" })).toBeInTheDocument();
    expect(screen.getByText("Advanced settings")).toBeInTheDocument();
  });

  it("saves valid essentials once and keeps the token field blank", async () => {
    const fetchMock = stubSettingsFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<SettingsPage />);
    const username = await screen.findByLabelText("Lichess username");
    await user.clear(username);
    await user.type(username, "ReplacementUser");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    expect(await screen.findByText("Settings saved locally.")).toBeInTheDocument();
    const saves = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(saves).toHaveLength(1);
    expect(saves[0][1]?.body).toContain("ReplacementUser");
    expect(screen.getByLabelText("Replace saved Lichess token")).toHaveValue("");
  });

  it("maps FastAPI validation errors to an accessible matching settings field", async () => {
    vi.stubGlobal("fetch", stubSettingsFetch(new Response(JSON.stringify({ detail: { errors: { default_player: "Use only letters, numbers, underscore or hyphen." } } }), { status: 400 })));
    const user = userEvent.setup();

    render(<SettingsPage />);
    const username = await screen.findByLabelText("Lichess username");
    await user.clear(username);
    await user.type(username, "bad name!");
    await user.click(screen.getByRole("button", { name: "Save settings" }));

    const error = await screen.findByText("Use only letters, numbers, underscore or hyphen.");
    const field = screen.getByLabelText("Lichess username");
    expect(error).toHaveAttribute("id", "default_player-error");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveAttribute("aria-describedby", "default_player-error");
  });

  it("requires deliberate confirmation before clearing the saved token", async () => {
    const fetchMock = stubSettingsFetch();
    vi.stubGlobal("fetch", fetchMock);
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    const user = userEvent.setup();

    render(<SettingsPage />);
    await screen.findByRole("heading", { level: 2, name: "Settings" });
    await user.click(screen.getByRole("button", { name: "Clear saved token" }));
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);

    await user.click(screen.getByRole("button", { name: "Clear saved token" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));
    expect(confirmMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls.at(-1)?.[1]?.body).toContain("clear_lichess_token");
  });
});
