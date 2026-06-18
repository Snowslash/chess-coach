# Lichess Study Create/Import Implementation Plan

**Goal:** Add explicit, token-gated commands that create a private/unlisted Lichess Study and import locally generated annotated PGN chapters into it.

**Architecture:** Keep the current local `export-annotated-pgn` command as the default safe workflow. Add a small stdlib HTTP client in `chess_coach/lichess_study.py`, then expose two separate CLI commands: `lichess-study-create` and `lichess-study-import`. Network side effects stay explicit; tests mock all HTTP calls; live API smoke is opt-in only.

**Tech stack:** Python 3.11+, stdlib `urllib.request`, `urllib.parse.urlencode`, existing `python-chess`/`pydantic`, pytest. Lichess endpoints from `https://lichess.org/api/openapi.yaml`: `POST /api/study` and `POST /api/study/{studyId}/import-pgn`, OAuth scope `study:write`.

---

## Boundaries

**Always do**

- Default visibility to `private`, not Lichess' API default of `unlisted`.
- Read token only from an env var, default `LICHESS_TOKEN`.
- Never print token values.
- Use form-encoded requests, not JSON.
- Mock all HTTP calls in tests.
- Cap/surface the Lichess 64-chapter study limit before import.
- Keep generated PGN, reports, env files and local coach state ignored.

**Ask first / explicit approval required**

- Any live Lichess API call.
- Any public Study visibility support.
- Any command that combines local export + network import in one step.

**Never in this slice**

- No hosted service.
- No GUI.
- No broad OAuth scopes.
- No token persistence.
- No mutation of original Lichess games.
- No editing old Study chapters after import.
- No committing personal PGNs or generated reports.

---

## Lichess API details to encode

### Create Study

Endpoint:

```text
POST https://lichess.org/api/study
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>
Scope: study:write
```

Required form fields from OpenAPI:

```text
name        string, 2-100 chars
visibility  public | unlisted | private
computer    nobody | owner | contributor | member | everyone
explorer    nobody | owner | contributor | member | everyone
cloneable   nobody | owner | contributor | member | everyone
shareable   nobody | owner | contributor | member | everyone
chat        nobody | owner | contributor | member | everyone
```

Optional:

```text
sticky=true|false
```

Conservative defaults for Chess Coach:

```python
{
    "visibility": "private",
    "computer": "owner",
    "explorer": "owner",
    "cloneable": "nobody",
    "shareable": "nobody",
    "chat": "nobody",
    "sticky": "true",
}
```

Expected success JSON:

```json
{"id": "9kze56XR"}
```

### Import PGN into Study

Endpoint:

```text
POST https://lichess.org/api/study/{studyId}/import-pgn
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer <token>
Scope: study:write
```

Required form field:

```text
pgn=<annotated PGN text>
```

Optional form fields:

```text
name         chapter name, 1-100 chars; omit for multi-game PGN so Lichess infers names from tags
orientation  white | black, default white
variant      standard etc.; default omit/standard
mode         practice | conceal | gamebook; default omit for normal analysis
```

Success JSON shape:

```json
{
  "chapters": [
    {"id": "iBjmYBya", "name": "test 2", "players": [{"name": "White"}, {"name": "Black"}], "status": "1-0"}
  ]
}
```

Lichess limit: one Study can contain at most 64 chapters. Multi-game PGN import can create multiple chapters.

---

## Dependency graph

```text
Task 1 token/error helpers
  -> Task 2 Study creation client
  -> Task 3 PGN import client
      -> Task 4 CLI commands
          -> Task 5 docs/env examples
              -> Task 6 optional live smoke, only with approval
```

---

## Task 1: Create Lichess Study client skeleton and auth helpers

**Objective:** Add a dedicated module with safe token lookup, redaction and typed exceptions.

**Files:**

- Create: `chess_coach/lichess_study.py`
- Create: `tests/test_lichess_study.py`

**RED tests:**

Add tests for:

```python
def test_token_from_env_returns_value(monkeypatch): ...
def test_token_from_env_rejects_missing_value(monkeypatch): ...
def test_auth_error_does_not_include_token_value(monkeypatch): ...
def test_build_headers_sets_bearer_without_logging_token(): ...
```

Expected first run:

```bash
uv run --extra dev python -m pytest tests/test_lichess_study.py -q
# FAIL: module/function missing
```

**GREEN implementation:**

Create:

```python
class LichessStudyError(RuntimeError):
    pass

class LichessAuthError(LichessStudyError):
    pass

class LichessApiError(LichessStudyError):
    pass


def token_from_env(name: str = "LICHESS_TOKEN") -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise LichessAuthError(f"Missing Lichess token env var: {name}")
    return value


def bearer_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "chess-coach/1.0",
    }
```

**Verification:**

```bash
uv run --extra dev python -m pytest tests/test_lichess_study.py -q
```

**Commit:**

```bash
git add chess_coach/lichess_study.py tests/test_lichess_study.py
git commit -m "feat: add lichess study auth helpers"
```

---

## Task 2: Add request/response helper with safe HTTP errors

**Objective:** Centralise form POSTs and make API failures readable without leaking secrets.

**Files:**

- Modify: `chess_coach/lichess_study.py`
- Modify: `tests/test_lichess_study.py`

**RED tests:**

Add tests with fake `urlopen` asserting:

- URL is correct.
- Body is `application/x-www-form-urlencoded`.
- Timeout is 30 seconds by default.
- HTTP 400 response text is included in `LichessApiError`.
- HTTP 429 says rate limit clearly.
- Token value is absent from exception text.

**Implementation sketch:**

```python
def _post_form(
    url: str,
    *,
    token: str,
    form: Mapping[str, str],
    urlopen=default_urlopen,
    timeout: int = 30,
) -> dict[str, Any]:
    body = urlencode(form).encode("utf-8")
    request = Request(url, data=body, headers=bearer_headers(token), method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            raise LichessApiError(f"Lichess rate limit hit on {url}: {detail}") from exc
        raise LichessApiError(f"Lichess API error {exc.code} on {url}: {detail}") from exc
    except URLError as exc:
        raise LichessApiError(f"Could not reach Lichess: {exc.reason}") from exc
    return json.loads(raw or "{}")
```

**Verification:**

```bash
uv run --extra dev python -m pytest tests/test_lichess_study.py -q
```

**Commit:**

```bash
git add chess_coach/lichess_study.py tests/test_lichess_study.py
git commit -m "feat: add lichess study request handling"
```

---

## Task 3: Implement `create_study`

**Objective:** Create a private/unlisted Study and return a typed reference.

**Files:**

- Modify: `chess_coach/lichess_study.py`
- Modify: `tests/test_lichess_study.py`

**RED tests:**

Add tests for:

```python
def test_create_study_posts_required_safe_defaults(): ...
def test_create_study_allows_unlisted_visibility(): ...
def test_create_study_rejects_public_visibility_by_default(): ...
def test_create_study_rejects_too_short_or_too_long_name(): ...
def test_create_study_returns_id_and_url(): ...
```

**Implementation API:**

```python
@dataclass(frozen=True)
class StudyRef:
    id: str
    url: str


def create_study(
    *,
    token: str,
    name: str,
    visibility: str = "private",
    base_url: str = "https://lichess.org",
    urlopen=default_urlopen,
) -> StudyRef:
    ...
```

**Validation:**

- `2 <= len(name) <= 100`
- `visibility in {"private", "unlisted"}`
- no `public` support in this slice
- response must contain non-empty `id`

**Form defaults:**

```python
form = {
    "name": name,
    "visibility": visibility,
    "computer": "owner",
    "explorer": "owner",
    "cloneable": "nobody",
    "shareable": "nobody",
    "chat": "nobody",
    "sticky": "true",
}
```

**Verification:**

```bash
uv run --extra dev python -m pytest tests/test_lichess_study.py -q
```

**Commit:**

```bash
git add chess_coach/lichess_study.py tests/test_lichess_study.py
git commit -m "feat: create private lichess studies"
```

---

## Task 4: Implement `import_pgn_to_study`

**Objective:** Import existing annotated PGN text as new Study chapters.

**Files:**

- Modify: `chess_coach/lichess_study.py`
- Modify: `tests/test_lichess_study.py`

**RED tests:**

Add tests for:

```python
def test_import_pgn_posts_to_study_import_endpoint(): ...
def test_import_pgn_includes_optional_single_chapter_name(): ...
def test_import_pgn_omits_name_for_multi_game_pgn_by_default(): ...
def test_import_pgn_rejects_empty_pgn(): ...
def test_import_pgn_rejects_more_than_64_games(): ...
def test_import_pgn_returns_created_chapter_refs(): ...
def test_import_pgn_surfaces_429_rate_limit(): ...
```

**Implementation API:**

```python
@dataclass(frozen=True)
class StudyChapterRef:
    id: str
    name: str
    url: str
    status: str | None = None

@dataclass(frozen=True)
class StudyImportResult:
    study_id: str
    study_url: str
    chapters: list[StudyChapterRef]


def import_pgn_to_study(
    *,
    token: str,
    study_id: str,
    pgn: str,
    name: str | None = None,
    orientation: str = "white",
    variant: str | None = None,
    mode: str | None = None,
    base_url: str = "https://lichess.org",
    urlopen=default_urlopen,
) -> StudyImportResult:
    ...
```

**PGN game count helper:**

Use `python-chess` rather than regex:

```python
def count_pgn_games(pgn: str) -> int:
    handle = io.StringIO(pgn)
    count = 0
    while chess.pgn.read_game(handle) is not None:
        count += 1
    return count
```

Rules:

- reject empty/whitespace PGN
- reject `>64` games before network request
- if multiple games and `name` is supplied, warn/omit because Lichess infers names when multiple chapters are created
- validate `orientation in {"white", "black"}`
- validate `mode in {"practice", "conceal", "gamebook"}` if provided
- default `variant` omitted, not hard-coded

**Verification:**

```bash
uv run --extra dev python -m pytest tests/test_lichess_study.py -q
```

**Commit:**

```bash
git add chess_coach/lichess_study.py tests/test_lichess_study.py
git commit -m "feat: import annotated pgn into lichess study"
```

---

## Task 5: Add CLI command `lichess-study-create`

**Objective:** Expose Study creation through an explicit networked command.

**Files:**

- Modify: `chess_coach/cli.py`
- Modify: `tests/test_cli.py`

**CLI shape:**

```bash
python -m chess_coach lichess-study-create \
  --name "Chess Coach Review 2026-06-17" \
  --visibility private \
  --token-env LICHESS_TOKEN
```

**RED tests:**

Add CLI tests using monkeypatch:

```python
def test_cli_lichess_study_create_uses_token_env_and_prints_url(...): ...
def test_cli_lichess_study_create_missing_token_returns_2_without_request(...): ...
def test_cli_lichess_study_create_rejects_public_visibility(...): ...
```

**Implementation notes:**

- Import `create_study`, `token_from_env`, `LichessStudyError` in `cli.py`.
- Add parser:

```python
create = sub.add_parser("lichess-study-create", help="Create a private/unlisted Lichess Study")
create.add_argument("--name", required=True)
create.add_argument("--visibility", choices=["private", "unlisted"], default="private")
create.add_argument("--token-env", default="LICHESS_TOKEN")
```

- On success print:

```text
Lichess Study created: https://lichess.org/study/<id>
Study ID: <id>
```

- On `LichessStudyError`, print to stderr and return `2`.

**Verification:**

```bash
uv run --extra dev python -m pytest tests/test_cli.py tests/test_lichess_study.py -q
```

**Commit:**

```bash
git add chess_coach/cli.py tests/test_cli.py
git commit -m "feat: add lichess study create command"
```

---

## Task 6: Add CLI command `lichess-study-import`

**Objective:** Import an already generated annotated PGN into an existing Study.

**Files:**

- Modify: `chess_coach/cli.py`
- Modify: `tests/test_cli.py`

**CLI shape:**

```bash
python -m chess_coach lichess-study-import \
  --study-id abc123 \
  --pgn reports/annotated/latest.pgn \
  --orientation white \
  --token-env LICHESS_TOKEN
```

Optional single-chapter name:

```bash
python -m chess_coach lichess-study-import \
  --study-id abc123 \
  --pgn reports/annotated/one-game.pgn \
  --name "Recent rapid review" \
  --token-env LICHESS_TOKEN
```

**RED tests:**

Add CLI tests:

```python
def test_cli_lichess_study_import_reads_pgn_and_prints_chapter_links(...): ...
def test_cli_lichess_study_import_missing_pgn_returns_2(...): ...
def test_cli_lichess_study_import_missing_token_returns_2_without_request(...): ...
def test_cli_lichess_study_import_passes_orientation_variant_mode(...): ...
```

**Implementation notes:**

Parser:

```python
import_cmd = sub.add_parser("lichess-study-import", help="Import annotated PGN into a Lichess Study")
import_cmd.add_argument("--study-id", required=True)
import_cmd.add_argument("--pgn", required=True)
import_cmd.add_argument("--name", default=None)
import_cmd.add_argument("--orientation", choices=["white", "black"], default="white")
import_cmd.add_argument("--variant", default=None)
import_cmd.add_argument("--mode", choices=["practice", "conceal", "gamebook"], default=None)
import_cmd.add_argument("--token-env", default="LICHESS_TOKEN")
```

Print success:

```text
Imported annotated PGN into: https://lichess.org/study/<study_id>
Chapters created: N
- <chapter name>: https://lichess.org/study/<study_id>/<chapter_id>
```

**Verification:**

```bash
uv run --extra dev python -m pytest tests/test_cli.py tests/test_lichess_study.py -q
```

**Commit:**

```bash
git add chess_coach/cli.py tests/test_cli.py
git commit -m "feat: add lichess study import command"
```

---

## Task 7: Add documentation and env example

**Objective:** Document token setup and the safe manual workflow.

**Files:**

- Modify: `README.md`
- Modify: `docs/runtime.md`
- Modify: `.env.example`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_release_readiness.py`

**RED tests:**

Extend release-readiness tests to require docs mention:

- `LICHESS_TOKEN`
- `study:write`
- `lichess-study-create`
- `lichess-study-import`
- private/unlisted default
- generated annotated PGNs are ignored

**Docs content:**

Add a section like:

```markdown
## Optional Lichess Study import

1. Create a Lichess OAuth token with only `study:write`.
2. Store it in ignored local config, e.g. `.env.stockfish`:

export LICHESS_TOKEN=...

3. Export local annotated PGN:

python -m chess_coach export-annotated-pgn --from reports/latest.json --out reports/annotated/latest.pgn --max-games 10 --critical-only

4. Create a private Study:

python -m chess_coach lichess-study-create --name "Chess Coach Review" --visibility private --token-env LICHESS_TOKEN

5. Import the PGN:

python -m chess_coach lichess-study-import --study-id <id> --pgn reports/annotated/latest.pgn --token-env LICHESS_TOKEN
```

Privacy note:

- `private` means only study members can view.
- `unlisted` means link-visible.
- Public Study support is intentionally absent in this slice.
- Import appends chapters; it does not edit original Lichess games.

**Verification:**

```bash
uv run --extra dev python -m pytest tests/test_release_readiness.py -q
```

**Commit:**

```bash
git add README.md docs/runtime.md .env.example CHANGELOG.md tests/test_release_readiness.py
git commit -m "docs: document lichess study import workflow"
```

---

## Task 8: Full local verification

**Objective:** Prove the feature is safe and does not regress existing workflows.

Run:

```bash
uv run --extra dev python -m pytest -q
python -m compileall -q chess_coach tests
bash -n scripts/run_report.sh scripts/setup_wsl.sh scripts/run_weekly_review.sh
git diff --check
git check-ignore -v reports/annotated/latest.pgn .env.stockfish .coach/state.json input/lichess_recent_your_lichess_username.pgn
```

Smoke without network:

```bash
python -m chess_coach analyse --pgn input/sample_games.pgn --out reports/smoke.md --mock
python -m chess_coach export-annotated-pgn --from reports/smoke.json --out reports/annotated/smoke.pgn --max-games 1 --critical-only
```

Expected:

- tests pass
- compileall passes
- shell scripts parse
- generated outputs remain ignored
- no command touches Lichess unless `lichess-study-*` is explicitly called with a token

---

## Task 9: Optional live Lichess smoke, only after explicit approval

**Objective:** Verify real API behaviour once using Sangeev's token.

Prerequisites:

```bash
export LICHESS_TOKEN=...
```

Commands:

```bash
python -m chess_coach lichess-study-create \
  --name "Chess Coach Smoke $(date +%F)" \
  --visibility private \
  --token-env LICHESS_TOKEN

python -m chess_coach lichess-study-import \
  --study-id <returned_id> \
  --pgn reports/annotated/smoke.pgn \
  --token-env LICHESS_TOKEN
```

Verify manually in browser:

- Study opens at `https://lichess.org/study/<id>`.
- Visibility is private or unlisted as requested.
- Chapter appears.
- Board loads from PGN.
- `Chess Coach:` comments appear on analysed/critical moves.

Do not automate browser login or token creation in this slice.

---

## Suggested implementation order

1. Implement Tasks 1-2: safe client foundation.
2. Implement Task 3: create Study.
3. Implement Task 4: import PGN.
4. Implement Tasks 5-6: CLI wrappers.
5. Implement Task 7: docs and release-readiness test.
6. Run Task 8 full local verification.
7. Stop and ask before Task 9 live smoke.

## Expected final user workflow

```bash
# Generate normal report first.
python -m chess_coach analyse \
  --pgn input/lichess_recent_your_lichess_username.pgn \
  --out reports/lichess_recent.md \
  --player your_lichess_username \
  --update-state

# Export board-review PGN locally.
python -m chess_coach export-annotated-pgn \
  --from reports/lichess_recent.json \
  --out reports/annotated/lichess_recent.pgn \
  --max-games 10 \
  --critical-only

# Network side effect: create a private study.
python -m chess_coach lichess-study-create \
  --name "Chess Coach Review" \
  --visibility private \
  --token-env LICHESS_TOKEN

# Network side effect: import PGN into the study.
python -m chess_coach lichess-study-import \
  --study-id <id> \
  --pgn reports/annotated/lichess_recent.pgn \
  --token-env LICHESS_TOKEN
```
