# sdr-manager First Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task, inline. Inline is the recommended route here because the user's token-budget rule prefers inline work on Opus. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude plugin that turns any team's sales exports into a weekly scorecard PDF with one coaching focus per rep, then prepares and records each 1:1.

**Architecture:** Three skills hold the judgment and a Python command-line tool holds the math. The tool inspects files safely, normalizes them into daily counts, calculates metrics and coaching focus, checks Claude's written numbers, and renders PDFs. Team data lives in a workspace folder outside the plugin.

**Tech Stack:** Python 3.9+ standard library, `unittest`, HTML and CSS templates, headless Chrome or Edge for PDF, Markdown skills. `coverage` is a development-only tool.

**Spec:** `docs/superpowers/specs/2026-10-30-sdr-manager-design.md`

## Global Constraints

- Runtime is Python 3.9 or newer, standard library only. `openpyxl` is optional and never required.
- Add `from __future__ import annotations` to every Python module so modern type hints work on 3.9.
- Tests use `unittest`, so they need no installs. `coverage` lives only in the local `.venv`.
- Tests must pass on both `python3` (3.12.9) and `/usr/bin/python3` (3.9.6).
- Coverage of `scripts/` must be at least 80%.
- Every command prints JSON to stdout. Exit codes: 0 success, 1 unexpected error, 2 the manager must decide something, 3 Python too old.
- Skills reference bundled files with `${CLAUDE_PLUGIN_ROOT}`. No fixed paths anywhere.
- Prospect names, emails, phones, and companies never reach stored history.
- Claude never sends messages or changes anything in a sales tool.
- Reports show status as text as well as color, list reps alphabetically, and contain no rankings.
- Every report shows the brand name from `assets/brand.json`, which is `Andy Gheewalla`, at the top of its first page, in every page footer, and in the document title.
- Python files stay under 800 lines and functions under 50 lines. Functions return new objects and don't mutate their inputs.
- Git: work on branch `first-build`, commit after each task, and use `<type>: <description>` messages. No attribution lines, because the user's git rule disables them.

## How to read this plan

Each task gives exact interfaces, test cases, and expected values. Full source listings are left out on purpose, because writing every line in the plan and again in the code would spend the user's usage limit twice. Code blocks appear only where logic is easy to get wrong. Test cases are requirements: each one becomes a real test, written before its implementation.

Standard test command:

```bash
python3 -m unittest discover -s tests -t .
```

## File structure

```text
sdr-plugin/
├── .gitignore
├── .claude-plugin/plugin.json
├── README.md
├── skills/{setup,scorecard,one-on-one}/SKILL.md
├── references/{file-mapping-guide,metric-definitions,coaching-playbook}.md
├── assets/
│   ├── brand.json             the report brand name
│   ├── default-targets.json
│   └── templates/{team-report.html,one-on-one.html,report.css}
├── scripts/
│   ├── sdr.py                 command-line entry point, argument parsing only
│   └── sdrlib/
│       ├── __init__.py
│       ├── environment.py     Python version, openpyxl, and browser checks
│       ├── targets.py         defaults, overrides, derived targets, ramp
│       ├── file_reader.py     read tables, masking, inspection
│       ├── profile.py         load team profile, match rep names
│       ├── normalize.py       apply mappings, stop rules
│       ├── history.py         read and write workspace history, week helpers
│       ├── metrics.py         pure calculations
│       ├── focus.py           statuses, focus rules, team pattern
│       ├── scorecard.py       assemble and save the metrics file
│       ├── coaching.py        read and append coaching history
│       ├── narrative_check.py compare written numbers with metrics
│       ├── reports.py         fill templates
│       ├── pdf.py             find a browser, print to PDF
│       └── workspace.py       create workspaces, load the sample
├── sample-data/               fake team profile and messy exports
└── tests/
    ├── __init__.py
    ├── helpers.py             path setup and shared fixture builders
    ├── make_sample_data.py    regenerates sample-data/ deterministically
    ├── fixtures/sample-mappings/
    └── test_*.py
```

`profile.py`, `history.py`, `scorecard.py`, `coaching.py`, `environment.py`, and `workspace.py` were added during planning so each file keeps one job. The spec's layout has been updated to match.

## Shared contracts

### Mapping file (`mappings/<name>.json`)

```json
{
  "signature": "sha256 of the lowercased headers joined by a newline",
  "kind": "activities",
  "header_row": 3,
  "date_format": "%m/%d/%Y",
  "columns": {"date": "Activity Date", "rep": "Assigned To", "action": "Type"},
  "fixed": {"channel": "call", "action": "dial"},
  "values": {"action": {"Call": "dial"}},
  "flags": {
    "connected": {"column": "Call Result", "true": ["Connected"], "false": ["No Answer", "Voicemail"]}
  }
}
```

- `kind` is `activities`, `rep_summary`, or `meetings`.
- A field comes from `columns` or `fixed`.
- Standard `channel` values are `call`, `email`, and `linkedin`.
- Standard `action` values are `dial`, `email`, `email_reply`, `email_bounce`, `li_request`, `li_accept`, `li_message`, `li_reply`, and `li_other`.
- Flags are `connected`, `replied`, `bounced`, and `accepted`. A blank flag cell counts as false.
- `rep_summary` adds a `week_start` column and any of the count columns from `ACTIVITY_COUNTS`.
- `meetings` uses columns `rep`, `booked_date`, `due_date`, `status`, and `accepted`, with `values` translating `status` and `accepted`.

### Row-to-count rules for `activities`

| Channel and action | Effect |
|---|---|
| `call`, `dial` | `dials` +1. Flag `connected` adds `connected` +1 |
| `email`, `email` | `emails` +1. Flags add `replies` and `bounces` |
| `email`, `email_reply` | `replies` +1 |
| `email`, `email_bounce` | `bounces` +1 |
| `linkedin`, `li_request` | `li_requests` +1. Flag `accepted` adds `li_accepted` +1 |
| `linkedin`, `li_accept` | `li_accepted` +1 |
| `linkedin`, `li_message` | `li_messages` +1. Flag `replied` adds `li_replies` +1 |
| `linkedin`, `li_reply` | `li_replies` +1 |
| `linkedin`, `li_other` | `li_other` +1 |

### Metrics file (`history/metrics/<week>.json`)

```json
{
  "schema_version": 1,
  "week": "2026-W44",
  "week_start": "2026-10-26",
  "week_end": "2026-11-01",
  "window_start": "2026-10-05",
  "window_end": "2026-11-01",
  "generated_at": "2026-10-30T12:00:00",
  "partial_week": false,
  "last_activity_date": "2026-10-30",
  "channels_present": ["call", "email", "linkedin"],
  "sources": [{"file": "calls.csv", "kind": "activities", "rows_read": 100, "rows_rejected": 0}],
  "targets": {"connect_rate": {"value": 0.054, "stretch": 0.133, "label": "Connect rate", "source": "Gong Labs 2024", "as_of": "2024-07"}},
  "minimums": {"connect_rate": 100},
  "team": {"totals": {}, "rates": {}, "meetings": {}, "status_counts": {}, "pattern": null},
  "reps": [{
    "name": "Ava Reyes",
    "slug": "ava-reyes",
    "status": "On track",
    "month_in_role": 18,
    "this_week": {"working_days": 5, "out": false, "counts": {}, "rates": {}, "meetings": {}},
    "window": {"working_days": 20, "days_active": 20, "counts": {}, "rates": {}, "meetings": {}, "targets": {"touches": 2080, "meetings_held": 9.2}},
    "steps": [{"number": 1, "name": "Activity", "status": "On target", "metric": "touches", "actual": 2160, "target": 2080}],
    "outcome": {"actual": 13, "target": 9.2, "status": "On target"},
    "focus": {"step": 2, "metric": "connect_rate", "actual": 0.07, "target": 0.133, "kind": "stretch"},
    "trend": {"weeks": ["2026-W41"], "touches": [540], "connect_rate": [0.07], "email_reply_rate": [0.05], "meetings_booked": [4], "meetings_held": [3]},
    "flags": [],
    "notes": []
  }],
  "notes": []
}
```

Status strings are exactly: `On target`, `Near`, `Below`, `Not enough data`, `Not available`. Rep statuses are exactly: `Onboarding`, `On track`, `Needs attention`, `Watch`, `Review`, `Limited data`.

### Narrative files

Claude writes these to `reports/<week>/`.

```json
{"headline": "", "observations": [""], "rep_notes": {"Ava Reyes": ""}}
```

```json
{"wins": [""], "focus_summary": "", "evidence": [""], "commitment_progress": [""], "questions": [""], "agenda": [""]}
```

### Time-off file (`history/time-off/<week>.json`)

```json
{"team_days_off": 1, "rep_days_off": {"Ben Carter": 2}}
```

### Commands

| Command | Purpose |
|---|---|
| `check-env` | Print Python version, `openpyxl` availability, and browser path |
| `init-workspace --path P [--sample]` | Create a workspace |
| `targets --workspace W` | Validate the profile and print resolved targets |
| `inspect FILE [--header-row N] [--workspace W]` | Print the safe preview |
| `normalize --workspace W --files F... [--week W]` | Store counts or report what's blocking |
| `metrics --workspace W [--week W]` | Build and save the metrics file |
| `check-narrative --workspace W --week W --narrative F [--rep NAME]` | Check written numbers |
| `report team --workspace W --week W --narrative F` | Build the team PDF |
| `report one-on-one --workspace W --week W --rep NAME --narrative F` | Build the 1:1 PDF |
| `log-coaching --workspace W --rep NAME --entry-file F` | Add a coaching entry |

---

### Task 1: Repository, manifest, and command shell

**Files:**
- Create: `.gitignore`, `.claude-plugin/plugin.json`, `scripts/sdr.py`, `scripts/sdrlib/__init__.py`, `scripts/sdrlib/environment.py`, `tests/__init__.py`, `tests/helpers.py`, `tests/test_cli.py`, `tests/test_plugin_files.py`

**Interfaces:**
- Produces: `environment.python_ok(version_info) -> bool`, `environment.find_browser() -> str | None`, `environment.report() -> dict`
- Produces: `sdr.main(argv: list[str]) -> int`, and `tests.helpers.run_cli(*args) -> tuple[int, dict]`, which calls `main` in-process and parses the JSON output

- [ ] **Step 1: Create the repository and development tools**

```bash
git init -b first-build
python3 -m venv .venv
.venv/bin/pip install coverage
```

`.gitignore` must contain `.venv/`, `__pycache__/`, `*.pyc`, `.coverage`, `htmlcov/`, `sdr-workspace/`, `sdr-demo/`, and `.DS_Store`.

- [ ] **Step 2: Write failing tests**

| Test | Expected |
|---|---|
| `plugin.json` parses | `name` is `sdr-manager`, `version` is `0.1.0`, author is `Manish Singh` |
| `python_ok((3, 8))` and `python_ok((3, 9))` | False, True |
| `check-env` | Exit 0, JSON with `python`, `openpyxl`, and `browser` keys |
| Unknown command | Exit 2 and a JSON `error` key, with no traceback |
| `find_browser` with every candidate missing | Returns None |

- [ ] **Step 3: Run the tests and confirm they fail**

Run the standard test command. Expected: errors because the modules don't exist.

- [ ] **Step 4: Implement**

`plugin.json` description: `Coach SDR teams from exported sales data: weekly scorecards, one coaching focus per rep, and 1:1 prep.` Keywords: `sales`, `sdr`, `coaching`, `scorecard`.

`find_browser` checks Chrome, Edge, Chromium, and Brave at standard macOS and Windows install paths, then `shutil.which` for `google-chrome`, `chromium`, `chromium-browser`, `microsoft-edge`, and `brave-browser`.

`sdr.py` adds its own folder to `sys.path`, exits 3 with a plain message if Python is too old, and converts `argparse` errors into JSON with exit 2.

- [ ] **Step 5: Run tests and validate**

```bash
python3 -m unittest discover -s tests -t .
claude plugin validate .
```

Expected: tests pass and validation succeeds.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: set up plugin skeleton, spec, and plan"
```

### Task 2: Targets and ramp

**Files:**
- Create: `assets/default-targets.json`, `scripts/sdrlib/targets.py`, `tests/test_targets.py`

**Interfaces:**
- Consumes: `profile.load_profile` is added in Task 4, so the `targets` command is wired up there.
- Produces:

```python
def load_defaults() -> dict
def resolve_targets(profile: dict, defaults: dict | None = None) -> dict
def derive_meeting_rate(targets: dict, channels: list[str]) -> float | None
def meetings_per_working_day(targets: dict) -> float
def month_in_role(start: date, on: date) -> int
def ramp_multiplier(month: int, ramp: dict) -> float
```

`default-targets.json` has top-level keys `targets`, `minimums`, `ramp`, and `near_band`:
- `targets` holds the twelve targets from spec section 8, each with `value`, `stretch`, `label`, `source`, and `as_of`. Keys: `dials_per_day`, `emails_per_day`, `linkedin_touches_per_day`, `connect_rate`, `email_reply_rate`, `li_accept_rate`, `li_reply_rate`, `meeting_rate`, `meetings_held_per_month`, `show_rate`, `acceptance_rate`, `bounce_limit`. `meeting_rate` has `value: null` and `derived: true`.
- `minimums` holds the sample sizes from spec section 8.3, using keys `connect_rate`, `email_reply_rate`, `li_accept_rate`, `li_reply_rate`, `meeting_rate`, `show_rate`, `acceptance_rate`.
- `ramp` is `{"1": 0.0, "2": 0.5, "3": 0.75}`. `near_band` is `0.85`.

- [ ] **Step 1: Write failing tests**

| Case | Expected |
|---|---|
| Defaults, all channels | `meeting_rate` 0.1209 (4 places), labeled as calculated |
| Channels `call`, `email` | 0.1525 |
| Channel `call` only | 0.2428 |
| Team sets `show_rate` to 0.70, all channels | Derived `meeting_rate` 0.1382 |
| Team sets `meeting_rate` to 0.10 | 0.10, with `source` of `team` |
| Team overrides `connect_rate` | Value changes, `source` is `team`, other targets untouched, and the input dict isn't mutated |
| `meetings_per_working_day` defaults × 20 | 9.23 (2 places) |
| Start Oct 1, on Oct 1 / Oct 30 / Oct 31 / Nov 30 / Dec 30 | Months 1 / 1 / 2 / 3 / 4 |
| `on` before `start` | Month 1 |
| Multipliers for months 1, 2, 3, 4, 12 | 0, 0.5, 0.75, 1, 1 |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement**

```python
def month_in_role(start: date, on: date) -> int:
    return max((on - start).days, 0) // 30 + 1
```

`derive_meeting_rate` follows spec section 8.1 exactly and returns None when no conversations are expected.

- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `feat: add starting targets and ramp rules`

### Task 3: File reading and safe inspection

**Files:**
- Create: `scripts/sdrlib/file_reader.py`, `tests/test_file_reader.py`
- Modify: `scripts/sdr.py` (add `inspect`)

**Interfaces:**

```python
@dataclass(frozen=True)
class Table:
    headers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]

class UnsupportedFile(Exception): ...

def read_table(path: Path, header_row: int = 1) -> Table
def header_signature(headers: Sequence[str]) -> str
def is_masked_column(name: str) -> bool
def mask_text(value: str) -> str
def inspect_file(path: Path, header_row: int = 1, mappings_dir: Path | None = None) -> dict
```

`inspect_file` returns `file`, `rows`, `header_row`, `headers`, `signature`, `preview` (first 10 lines as cells), `distinct`, `masked_columns`, and `matched_mapping`.

- [ ] **Step 1: Write failing tests**

| Case | Expected |
|---|---|
| UTF-8 file with a byte-order mark | First header has no stray characters |
| Windows-1252 file containing `é` | Reads correctly |
| Semicolon-delimited and tab-delimited files | Columns split correctly |
| Header on line 3 with `header_row=3` | Headers and rows correct |
| Short rows, long rows, blank lines | Padded, trimmed, skipped |
| `.xlsx` with `openpyxl` unavailable (patched import) | `UnsupportedFile` naming the Save as CSV fix |
| `.xlsx` with `openpyxl` available (skip if missing) | Dates read as ISO text |
| `.pdf` file | `UnsupportedFile` |
| `is_masked_column` for `Email`, `Contact Name`, `Company`, `Prospect` | True |
| `is_masked_column` for `Contact Owner`, `Account Owner`, `Assigned To`, `Lead Rep`, `Lead Representative`, `Call Result` | False |
| `is_masked_column` for `Email Status`, `Lead Status`, `Phone Disposition`, `Email Sent Date` | False |
| `mask_text("reach me at a.b@c.co or 415-555-0100 today")` | No address or number remains |
| Preview of a file with a masked column and a free-text note holding an email | Neither value appears anywhere in the output |
| Column with 31 distinct values | Not in `distinct` |
| Column with 30 distinct values | In `distinct` |
| Masked column with 3 distinct values | Not in `distinct` |
| Headers differing only by case | Same signature |
| Saved mapping with a matching signature at its own `header_row` | `matched_mapping` is that file's name |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement**

Decode with `utf-8-sig`, then fall back to `cp1252`. Choose the delimiter by counting `,`, `;`, and tab in the header line. Masked values become `[masked]`. Email and phone patterns are applied to every preview cell, including lines above the header.

```python
MASKED_WORDS = ("email", "phone", "mobile", "contact", "prospect", "lead",
                "first name", "last name", "company", "account")
VISIBLE_WORDS = ("owner", "rep", "representative", "sdr", "user", "assigned", "agent",
                 "status", "result", "outcome", "disposition", "type", "date", "sent",
                 "replied", "bounced", "opened", "stage", "step")
```

Match whole words, ignoring case. A column is masked when it contains a masked word and no visible word. The email and phone patterns still apply to visible columns.

- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `feat: read exports and preview them safely`

### Task 4: Profile, normalization, and history

**Files:**
- Create: `scripts/sdrlib/profile.py`, `scripts/sdrlib/normalize.py`, `scripts/sdrlib/history.py`, `tests/test_profile.py`, `tests/test_normalize.py`, `tests/test_history.py`
- Modify: `scripts/sdr.py` (add `targets`, `normalize`)

**Interfaces:**

```python
# profile.py
class ProfileError(Exception): ...
def load_profile(workspace: Path) -> dict
def rep_lookup(profile: dict) -> dict[str, str | None]
def rep_slug(name: str) -> str

# history.py
ACTIVITY_COUNTS = ("dials", "connected", "emails", "replies", "bounces", "li_requests",
                   "li_accepted", "li_messages", "li_replies", "li_other")
ACTIVITY_FIELDS = ("date", "rep", "channel", "granularity") + ACTIVITY_COUNTS
MEETING_FIELDS = ("rep", "booked_date", "due_date", "status", "accepted")
def iso_week(d: date) -> str
def week_bounds(week: str) -> tuple[date, date]
def previous_weeks(week: str, count: int) -> list[str]
def merge_activity(existing: list[dict], new: list[dict]) -> list[dict]
def write_activity(workspace: Path, rows: list[dict]) -> None
def read_activity(workspace: Path, weeks: list[str]) -> list[dict]
def write_meetings(workspace: Path, week: str, rows: list[dict]) -> None
def read_latest_meetings(workspace: Path) -> list[dict] | None
def write_sources(workspace: Path, week: str, sources: list[dict]) -> None
def read_sources(workspace: Path, week: str) -> list[dict]
def read_time_off(workspace: Path, week: str) -> dict
def latest_week(workspace: Path) -> str | None

# normalize.py
@dataclass(frozen=True)
class FileResult:
    file: str
    kind: str
    rows_read: int
    rows_rejected: int
    activity: tuple[dict, ...]
    meetings: tuple[dict, ...]
    unknown_reps: dict
    unmapped: dict
    rejected_examples: tuple[str, ...]

def find_mapping(path: Path, mappings_dir: Path) -> dict | None
def normalize_file(path: Path, mapping: dict, reps: dict) -> FileResult
def channel_conflicts(results: Sequence[FileResult]) -> dict[str, list[str]]
def normalize_files(workspace: Path, files: Sequence[Path], week: str | None = None) -> dict
```

`rep_lookup` maps lowercased names and aliases to the canonical name, and maps `ignored_names` to None.

`normalize_files` returns `status` (`ok` or `needs_input`), `week`, `files`, `files_without_mapping`, `unknown_reps`, `unmapped_values`, `rejected_examples`, and `channel_conflicts`. **It stores nothing unless every file passes.** The `normalize` command exits 2 on `needs_input`.

- [ ] **Step 1: Write failing tests**

| Module | Case | Expected |
|---|---|---|
| profile | Missing file | `ProfileError` pointing to setup |
| profile | Rep without `name`, or an invalid channel | `ProfileError` naming the problem |
| profile | Alias and different case in lookup | Same canonical name |
| profile | Ignored name | Maps to None |
| profile | `rep_slug("Ana María O'Neil")` | `ana-maria-oneil` |
| history | `iso_week(date(2026, 10, 26))` | `2026-W44` |
| history | `week_bounds("2026-W44")` | Oct 26 to Nov 1 |
| history | `previous_weeks("2026-W02", 4)` | Crosses the year boundary correctly, oldest first, ending in `2026-W02` |
| history | Merge stored Oct 5 to 9 with import Oct 7 to 8 for `call` | Oct 5, 6, 9 kept and Oct 7, 8 replaced |
| history | Same merge, `email` rows on those dates | Email rows untouched |
| history | Import range with a date where a rep has no new rows | Old row for that date is removed |
| history | Same import written twice | Stored files are byte-identical |
| history | `week` row for a channel | Replaces that channel's rows for Monday to Sunday |
| history | Two meeting snapshots | `read_latest_meetings` returns the newest |
| history | No snapshot | Returns None |
| history | Missing time-off file | `{"team_days_off": 0, "rep_days_off": {}}` |
| normalize | Each row in the row-to-count table | Correct daily counts |
| normalize | 3 rows, 1 rep, 1 day, 2 connected | One row: `dials` 3, `connected` 2 |
| normalize | Alias in file | Canonical rep name stored |
| normalize | Ignored name | Rows left out, with no error |
| normalize | Unknown rep | Reported with row count, nothing stored |
| normalize | New value in a flag column | Reported under `unmapped_values`, nothing stored |
| normalize | Blank flag cell | Treated as false |
| normalize | Unparseable date, or blank rep | Row rejected and counted |
| normalize | 6 of 100 rows rejected | `needs_input` |
| normalize | 5 of 100 rows rejected | `ok` |
| normalize | Footer row `Total rows: 100` | Rejected and counted |
| normalize | Rejected row holding an email and a contact name | `rejected_examples` shows neither |
| normalize | Two files mapped to `call` | `channel_conflicts` names both |
| normalize | File with no matching mapping | Listed in `files_without_mapping` |
| normalize | `rep_summary` row with call and email columns | Two rows, `granularity` `week`, dated Monday |
| normalize | Summary row whose date isn't a Monday | Dated the Monday of that week |
| normalize | Meetings with a missing due date | Due date equals booked date, with a note |
| normalize | Meetings with `accepted` column blank | `pending` |
| normalize | Meetings with no `accepted` column | Stored blank |
| normalize | Stored activity and meeting files | Contain only the standard fields, no prospect data |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement** in the order `profile.py`, `history.py`, `normalize.py`, then wire up the commands

The covered dates for a channel are every date from that import's earliest to latest date. For `week` rows they are Monday to Sunday of each week present.

Without `--week`, the meetings snapshot is labeled with the latest week in this import's activity rows. If the import has none, it uses the week of the latest booked date.

- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `feat: normalize exports into stored daily counts`

### Task 5: Metric calculations

**Files:**
- Create: `scripts/sdrlib/metrics.py`, `tests/test_metrics.py`
- Modify: `tests/helpers.py` (add the shared fixture below)

**Interfaces:**
- Consumes: `history.week_bounds`, `history.ACTIVITY_COUNTS`, `targets.month_in_role`, `targets.ramp_multiplier`, `targets.meetings_per_working_day`
- Produces:

```python
def sum_counts(rows: Iterable[dict]) -> dict
def touches(counts: dict) -> int
def conversations(counts: dict) -> int
def calculate_rates(counts: dict) -> dict
def meeting_rate(booked: int, conversation_count: int) -> float | None
def meeting_summary(meetings: Iterable[dict], start: date, end: date) -> dict
def working_days(week: str, time_off: dict, rep: str, last_date: date | None = None) -> int
def days_active(rows: Iterable[dict]) -> int | None
def touch_target_per_day(targets: dict, channels: list[str]) -> float
def window_targets(rep: dict, weeks: list[str], time_off: dict, targets: dict,
                   channels: list[str], last_date: date | None) -> dict
```

Rate keys: `connect_rate`, `email_reply_rate`, `bounce_rate`, `li_accept_rate`, `li_reply_rate`. A rate with a zero denominator is None.

`meeting_summary` keys: `booked`, `due`, `held`, `no_show`, `cancelled`, `accepted_yes`, `accepted_no`, `pending`, `show_rate`, `acceptance_rate`. `booked` uses `booked_date`. All other keys use `due_date`.

In the metrics file, `window.rates` holds the rate keys above plus `meeting_rate`, and `window.meetings` holds the `meeting_summary` output, or null when no meetings file exists.

`window_targets` returns `working_days`, `touches`, and `meetings_held`.

**Shared fixture** (`tests/helpers.py`): one rep with 20 working days from `2026-W41` to `2026-W44`.

```python
WINDOW_COUNTS = {"dials": 880, "connected": 48, "emails": 820, "replies": 28, "bounces": 10,
                 "li_requests": 190, "li_accepted": 57, "li_messages": 190, "li_replies": 19,
                 "li_other": 0}
# Meetings: 12 booked in the window. 9 held, 2 no-show, 1 cancelled. Of the held: 6 yes, 3 no.
```

- [ ] **Step 1: Write failing tests**

Hand-worked answers for the fixture:

| Metric | Expected |
|---|---|
| Touches | 2,080 |
| Connect rate | 0.054545 |
| Email reply rate | 0.034146 |
| Bounce rate | 0.012195 |
| LinkedIn acceptance rate | 0.300000 |
| LinkedIn reply rate | 0.100000 |
| Conversations | 95 |
| Meeting rate | 0.126316 |
| Show rate | 0.750000 |
| Acceptance rate | 0.666667 |
| Touch target | 2,080 |
| Meetings held target | 9.23 |

Other cases:

| Case | Expected |
|---|---|
| Zero dials | `connect_rate` None |
| Meeting booked in the window, due after it | Counted in `booked`, not in `due` |
| Rescheduled and scheduled meetings | Left out of `due` |
| Pending meeting | Left out of `acceptance_rate`, counted in `pending` |
| Blank `accepted` on every row | `acceptance_rate` None, `pending` 0 |
| 1 team day off, 2 rep days off | 2 working days |
| 5 rep days off | 0 working days |
| Data ending Wednesday with `last_date` | 3 working days before time off |
| Weekend touches | Counted in totals, working days unchanged |
| Start date 2026-09-20, window W41 to W44 | Multipliers 0, 0, 0.5, 0.5. Touch target 520. Meetings target 2.31 |
| No start date | Multiplier 1 and a note |
| Channels `call`, `email` only | Touch target per day 85 |
| Rows with `granularity` `week` | `days_active` None |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `feat: calculate rep metrics and window targets`

### Task 6: Status, coaching focus, and the scorecard file

**Files:**
- Create: `scripts/sdrlib/focus.py`, `scripts/sdrlib/scorecard.py`, `tests/test_focus.py`, `tests/test_scorecard.py`
- Modify: `scripts/sdr.py` (add `metrics`)

**Interfaces:**
- Consumes: Tasks 2, 4, and 5
- Produces:

```python
# focus.py
def compare(actual: float | None, target: float | None, enough_data: bool = True,
            near_band: float = 0.85) -> str
def evaluate_steps(window: dict, targets: dict, minimums: dict, near_band: float) -> list[dict]
def evaluate_outcome(window: dict, near_band: float) -> dict
def stretch_focus(window: dict, targets: dict, minimums: dict) -> dict | None
def gap_focus(step: dict) -> dict
def choose_status(steps: list[dict], outcome: dict, onboarding: bool, stretch: dict | None) -> dict
def team_pattern(reps: list[dict]) -> dict | None
def bounce_flag(window: dict, targets: dict) -> bool

# scorecard.py
def build_scorecard(workspace: Path, week: str | None = None, now: datetime | None = None) -> dict
```

`gap_focus` copies `step`, `metric`, `actual`, and `target` from the step and sets `kind` to `gap`. `stretch_focus` sets `kind` to `stretch`.

`choose_status` returns `{"status": str, "focus": dict | None}`. The order is the spec's section 9.2 and must not change:

```python
def choose_status(steps, outcome, onboarding, stretch):
    if onboarding:
        return {"status": "Onboarding", "focus": None}
    step5 = steps[4]["status"]
    if outcome["status"] == "On target" and step5 != "Below":
        return {"status": "On track", "focus": stretch}
    for wanted, status in (("Below", "Needs attention"), ("Near", "Watch")):
        for step in steps:
            if step["status"] == wanted:
                return {"status": status, "focus": gap_focus(step)}
    if outcome["status"] in ("Near", "Below"):
        return {"status": "Review", "focus": None}
    return {"status": "Limited data", "focus": None}
```

`compare` returns `Not available` when actual or target is None or target is 0, then `Not enough data` when `enough_data` is False, then applies the bands. Compare raw values, never rounded ones.

Step 2 picks the metric with the lowest actual ÷ target among metrics with enough data. If none has enough data but some have values, the step is `Not enough data`. If none has values, it's `Not available`.

A channel counts as present if any active rep has rows for it in the window.

- [ ] **Step 1: Write failing tests**

| Case | Expected |
|---|---|
| Shared fixture | Steps: On target, Near, On target, Near, On target. Outcome Near. Status `Watch`, focus step 2, metric `li_reply_rate` |
| Actual exactly at target | `On target` |
| Actual at exactly 85% | `Near` |
| Actual at 84.9% | `Below` |
| Month-1 rep with strong numbers | `Onboarding`, no focus |
| Held meets target, all steps fine | `On track` with stretch focus on `connect_rate` |
| Held meets target, step 1 Below | `On track` |
| Held meets target, step 5 Below | `Needs attention`, step 5 |
| Steps 2 and 4 Below | `Needs attention`, step 2 |
| Step 3 Near, nothing Below | `Watch`, step 3 |
| Held under target, every step On target | `Review` |
| Held under target, no step has enough data | `Review` |
| No meetings file, steps 1 and 2 fine | `Limited data`, steps 3 to 5 and outcome `Not available` |
| No meetings file, step 1 Below | `Needs attention`, step 1 |
| Zero working days in the window | Count targets `Not available`, status `Limited data` |
| Actual above both stretch values | `On track`, no focus |
| Reviewed meetings 4, minimum 5 | Step 5 `Not enough data`, skipped |
| Bounce 2.0% on 100 emails | Flag raised |
| Bounce 1.9% on 100 emails | No flag |
| Bounce 5% on 50 emails | No flag |
| 3 of 6 judged reps share step 2 | Pattern for step 2 |
| 2 of 4 judged reps share step 2 | No pattern, fewer than three |
| 3 of 7 judged reps share step 2 | No pattern, under half |
| 3 of 8 reps share step 2, and 2 of the 8 are Onboarding or Limited data | Pattern for step 2, because those 2 aren't judged |
| On track reps with a stretch focus | Count as judged, but never as sharing a step |
| `build_scorecard` on a small workspace | Saves `history/metrics/2026-W44.json` with every key in the contract |
| Selected week with no activity | Exit 2 with a plain message |
| Inactive rep | Left out of `reps` and team totals |
| Latest date before Friday | `partial_week` true, working days reduced |
| Rep with zero working days this week | `this_week.out` true |
| Reps in input order B, A | Output sorted alphabetically |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement** `focus.py`, then `scorecard.py`, then the `metrics` command
- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `feat: choose rep status and coaching focus`

### Task 7: Coaching history and number checking

**Files:**
- Create: `scripts/sdrlib/coaching.py`, `scripts/sdrlib/narrative_check.py`, `tests/test_coaching.py`, `tests/test_narrative_check.py`
- Modify: `scripts/sdr.py` (add `check-narrative`, `log-coaching`)

**Interfaces:**

```python
# coaching.py
def coaching_path(workspace: Path, rep: str) -> Path
def read_history(workspace: Path, rep: str) -> str
def append_entry(workspace: Path, rep: str, entry: dict, today: date) -> Path

# narrative_check.py
def extract_numbers(text: str) -> list[str]
def allowed_numbers(metrics: dict, coaching_text: str = "") -> set[str]
def check_narrative(narrative: dict, metrics: dict, coaching_text: str = "") -> list[dict]
```

A coaching entry takes `focus`, `agreed` (list), `check_by`, and `notes`, and is stored as:

```markdown
## 2026-10-30
- Focus: Response (connect rate)
- Agreed: First agreed action
- Agreed: Second agreed action
- Check by: 2026-11-13
- Notes: Free text
```

Each problem from `check_narrative` holds `field`, `text`, and `number`. The `check-narrative` command exits 2 if there are any.

- [ ] **Step 1: Write failing tests**

| Case | Expected |
|---|---|
| Entry appended twice | Both kept, oldest first |
| History for a rep with no file | Empty string |
| Rep name with an apostrophe | Uses the slug file name |
| Entry missing `agreed` | `ValueError` naming the field |
| `extract_numbers("Connect rate hit 5.5% on 880 dials")` | `5.5%`, `880` |
| Text with `2026-10-30`, `2026-W44`, `Oct 30`, `Step 3`, `1:1` | Nothing extracted |
| Number with a comma, `2,080` | Extracted and matched against 2080 |
| Rate 0.054545 in metrics, text says `5.5%` | Passes |
| Text says `5.6%` | One problem |
| Target 9.23, text says `9.2` | Passes |
| Text says `12` when 12 appears in metrics | Passes |
| Text says `3` with no 3 in metrics | One problem |
| Text says `50 dials` found only in coaching history | Passes when history is supplied, fails when it isn't |
| Numbers nested in lists and `rep_notes` | All checked, and `field` shows where |
| The word `four-week` | Nothing extracted |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement**

`allowed_numbers` walks the metrics JSON, skipping `generated_at`, and adds these display forms:
- Whole numbers: `str(n)` and `f"{n:,}"`
- Values between 0 and 1: `f"{v * 100:.1f}"`, the same with `%`, and `f"{v * 100:.2f}%"`
- Other decimals: `f"{v:.1f}"`, `f"{v:.2f}"`

Compare after removing commas.

- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `feat: keep coaching history and check written numbers`

### Task 8: Reports and PDF

**Files:**
- Create: `assets/brand.json`, `assets/templates/team-report.html`, `assets/templates/one-on-one.html`, `assets/templates/report.css`, `scripts/sdrlib/reports.py`, `scripts/sdrlib/pdf.py`, `tests/test_reports.py`, `tests/test_pdf.py`
- Modify: `scripts/sdr.py` (add `report`)

**Interfaces:**

```python
# reports.py
def load_brand() -> str
def format_value(metric: str, value: float | int | None) -> str
def sparkline(values: Sequence[float | None]) -> str
def render_team(metrics: dict, narrative: dict) -> str
def render_one_on_one(metrics: dict, rep: str, narrative: dict, coaching_text: str) -> str

# pdf.py
def print_to_pdf(html_path: Path, pdf_path: Path, browser: str | None = None,
                 runner: Callable = subprocess.run) -> bool
```

Render with `string.Template`. Every data value goes through `html.escape`. The `report` command first runs the number check and exits 2 if it fails. It saves HTML to `reports/<week>/`, then the PDF, and reports `pdf`, `html`, and `fallback`.

**Branding:** `assets/brand.json` contains `{"name": "Andy Gheewalla"}`. `load_brand` reads it. Show the name as a wordmark above the report title on the first page, as `Andy Gheewalla | Team report | 2026-W44` in the footer of every `.page` section, and at the start of the HTML `<title>`, which becomes the PDF document title. The 1:1 footer uses `Andy Gheewalla | 1:1 prep | <rep> | <week>`.

**Visual direction:** a printed ledger. Georgia headings, system sans-serif tabular numbers, thin rules instead of boxes, and a generous left column for the rep's focus. Colors are defined once as custom properties in `report.css`.

```css
:root {
  --ink: #1b1f23; --muted: #5b6570; --rule: #d7dde3; --paper: #fff; --accent: #0f5c5c;
  --on-target: #1c7c54; --near: #a86a00; --below: #b3261e; --unavailable: #6b7280;
}
@page { size: Letter; margin: 14mm; }
```

Status uses text plus a shape: `● On target`, `◐ Near`, `○ Below`, `– Not enough data`, `– Not available`.

- [ ] **Step 1: Write failing tests**

| Case | Expected |
|---|---|
| `load_brand()` | `Andy Gheewalla` |
| Team report with 3 reps | Brand appears in the first-page header and in the footer of all 5 pages |
| 1:1 report | Brand appears in the header and the footer |
| Both reports | `<title>` starts with the brand name |
| Brand name containing `&` (patched) | Escaped in output |
| `format_value("connect_rate", 0.054545)` | `5.5%` |
| `format_value("touches", 2080)` | `2,080` |
| `format_value("connect_rate", None)` | `Not available`, never `0` |
| Sparkline with a None value | Valid SVG with a gap |
| Team report with reps Ava, Ben | Ava's page appears before Ben's |
| Team report | Contains no `rank` or leaderboard language |
| Every step status | Shown as words |
| Rep name `<script>alert(1)</script>` | Escaped in output |
| Observations list of 5 | Only 3 rendered |
| `partial_week` true | Banner shown |
| Source file with 3 rejected rows | Row counts and date range shown |
| Pattern present | Team pattern section shown |
| Final page | Lists every target with source and date |
| Bounce flag | Deliverability warning on the rep's page |
| 1:1 report | Contains wins, focus, commitments, questions, and agenda sections |
| 1:1 for an unknown rep | `ValueError` naming the rep |
| Number check failing during `report` | Exit 2, no files written |
| `print_to_pdf` with a fake runner that writes `%PDF-` | True |
| Runner raises `TimeoutExpired`, or writes no file | False, HTML kept |
| `browser=None` and none found | False |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement**

`print_to_pdf` runs the browser with `--headless=new`, `--disable-gpu`, `--no-pdf-header-footer`, a temporary `--user-data-dir`, and `--print-to-pdf`, with `timeout=60`. Success means the file exists and starts with `%PDF`.

- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Render a real sample and look at it**

Build one team report and one 1:1 report from test data, then open both PDFs with the Read tool. Fix anything that overflows a page, breaks a table, or reads poorly in grayscale.

- [ ] **Step 6: Commit** with message `feat: render team and one-on-one PDF reports`

### Task 9: Workspaces and the sample team

**Files:**
- Create: `scripts/sdrlib/workspace.py`, `tests/make_sample_data.py`, `sample-data/team-profile.json`, `sample-data/exports/*.csv`, `tests/fixtures/sample-mappings/*.json`, `tests/test_workspace.py`, `tests/test_sample_team.py`
- Modify: `scripts/sdr.py` (add `init-workspace`)

**Interfaces:**

```python
def init_workspace(path: Path, sample: bool = False) -> dict
```

It creates `imports/`, `mappings/`, `history/`, `reports/`, `coaching/`, a `.gitignore` containing `*`, and a starter `team-profile.json`. With `sample=True` it copies the sample profile and places the exports in `imports/2026-W44/`, with no mappings, so the demo exercises the mapping step. An existing workspace is left untouched and reported with `already_exists: true`.

**Sample exports** (all fake, generated deterministically with `random.Random(44)`):

| File | Mess it includes |
|---|---|
| `crm-calls.csv` | Two report lines above the header, `MM/DD/YYYY` dates, a `Total rows` footer. Columns: `Activity Date`, `Assigned To`, `Call Result`, `Contact Name`, `Contact Phone`, `Company` |
| `sequencer-emails.csv` | Semicolons, timestamps, `Yes` and `No` flags. Columns: `Sent At`, `Owner`, `Recipient Email`, `Step`, `Bounced`, `Replied` |
| `linkedin-activity.csv` | One column mixes requests and messages. Columns: `Date`, `Rep`, `Action`, `Result`, `Prospect` |
| `crm-meetings.csv` | Columns: `Owner Name`, `Date Booked`, `Meeting Date`, `Meeting Status`, `AE Decision`, `Account` |

Weeks `2026-W40` to `2026-W44`. Touches are spread evenly across Monday to Friday. Meetings are booked on a Tuesday and due that Thursday, cycling through `2026-W41` to `2026-W44`, so window totals match exactly. Booked meetings beyond a rep's held, no-show, and cancelled total have status `Scheduled` and are due the Thursday after the window. Use phone numbers in the `555-01xx` range and `example.com` addresses.

Four-week totals by rep (weekly values are the total ÷ 4, and `2026-W40` repeats the weekly values):

| Rep | Dials / conn. | Emails / replies / bounces | LI req. / acc. | LI msg. / rep. | Booked | Held / no-show / canc. | Yes / no / pend. |
|---|---|---|---|---|---|---|---|
| Ava Reyes | 920 / 64 | 840 / 44 / 8 | 200 / 60 | 200 / 24 | 17 | 13 / 2 / 0 | 9 / 3 / 1 |
| Ben Carter | 400 / 24 | 400 / 16 / 4 | 80 / 24 | 80 / 8 | 6 | 4 / 1 / 0 | 3 / 1 / 0 |
| Chloe Nguyen | 960 / 28 | 920 / 12 / 28 | 200 / 60 | 200 / 24 | 8 | 6 / 1 / 0 | 4 / 2 / 0 |
| Diego Marin | 900 / 64 | 840 / 40 / 8 | 200 / 60 | 200 / 24 | 6 | 5 / 1 / 0 | 3 / 1 / 1 |
| Priya Shah | 900 / 64 | 840 / 40 / 8 | 200 / 60 | 200 / 24 | 16 | 7 / 7 / 1 | 5 / 2 / 0 |
| Sam Okafor | 900 / 64 | 840 / 40 / 8 | 200 / 60 | 200 / 24 | 16 | 13 / 2 / 0 | 4 / 9 / 0 |
| Nina Patel | 360 / 15 (W42 to W44) | 300 / 9 / 3 | 60 / 15 | 60 / 6 | 2 | 1 / 0 / 0 | 0 / 0 / 1 |

Start dates: Nina Patel `2026-10-12`. Everyone else starts in 2025.

- [ ] **Step 1: Write failing tests**

| Case | Expected |
|---|---|
| `init_workspace` on a new path | Folders, `.gitignore`, and profile created |
| `init_workspace` on an existing workspace | Nothing overwritten, `already_exists` true |
| Sample workspace | Exports in `imports/2026-W44/`, `mappings/` empty |
| Generator run twice | Identical files |
| Full pipeline with fixture mappings | Each rep gets the result below |

| Rep | Status | Focus |
|---|---|---|
| Ava Reyes | On track | Stretch, `connect_rate` |
| Ben Carter | Needs attention | Step 1 |
| Chloe Nguyen | Needs attention | Step 2, `email_reply_rate`, with a bounce flag |
| Diego Marin | Needs attention | Step 3 |
| Priya Shah | Needs attention | Step 4 |
| Sam Okafor | Needs attention | Step 5 |
| Nina Patel | Onboarding | None |

Also check: no team pattern, and no name, email, or phone from the exports appears in any stored `history/` file.

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Implement** the workspace code, generator, and fixture mappings, then run:

```bash
python3 tests/make_sample_data.py
```

- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `feat: add workspaces and a seven-rep sample team`

### Task 10: Skills, references, and README

**Files:**
- Create: `skills/setup/SKILL.md`, `skills/scorecard/SKILL.md`, `skills/one-on-one/SKILL.md`, `references/file-mapping-guide.md`, `references/metric-definitions.md`, `references/coaching-playbook.md`, `README.md`
- Modify: `tests/test_plugin_files.py`

**Interfaces:**
- Consumes: every command in the Shared contracts table

Every skill's frontmatter has `name`, `description` (third person with trigger phrases), and `argument-hint`. Bodies use imperative instructions, stay under 3,000 words, and try `python3`, then `python`, then `py -3`.

- [ ] **Step 1: Write failing tests**

| Case | Expected |
|---|---|
| Each `SKILL.md` | Valid frontmatter, and `name` matches its folder |
| Each `SKILL.md` | Under 3,000 words and uses `${CLAUDE_PLUGIN_ROOT}` |
| Every plugin text file | No `/Users/` or other fixed home paths |
| Each reference file | Named by at least one skill |
| Every command in `sdr.py` | Named by at least one skill |
| `README.md` | Mentions requirements, install, privacy, tested platforms, and sample data |

- [ ] **Step 2: Run the tests and confirm they fail**
- [ ] **Step 3: Write the content**

**`setup`** follows spec section 4.1. It must include:
- The `check-env` step and plain Python install steps for macOS and Windows
- The sample path through `init-workspace --sample`, then the suggestion to run the scorecard
- The team profile schema and the small-batch questions
- `targets` to validate, plus a summary of which targets are built-in and which are the team's
- A warning that coaching notes are sensitive and shouldn't sit in a shared folder

**`scorecard`** follows spec section 4.2. It must include:
- On a first run, asking for the last four full weeks plus the current week
- Asking for a meetings export that covers at least the last six weeks
- Reusing `matched_mapping` without asking
- How to explain a mapping in plain language and get confirmation, pointing to `references/file-mapping-guide.md`
- Writing the time-off file with the exact schema
- What to do with each `needs_input` field from `normalize`
- Rules for written text: cite only numbers from the metrics file, spell out other numbers, frame causes as questions, and never rank reps
- The fixed order: `metrics`, write narrative, `check-narrative`, `report team`
- Handling `fallback: true` with Save as PDF steps
- The final chat summary, including data warnings

**`one-on-one`** follows spec section 4.3. It must include:
- Finding the latest metrics file and warning when `generated_at` is more than 7 days old
- Using optional notes and transcripts without scoring them
- Reading `references/coaching-playbook.md` for the focus step
- The `--log` flow, with confirmation before `log-coaching`
- The HR rule: offer the facts, recommend no employment action, suggest involving HR

**`references/file-mapping-guide.md`:** the mapping contract, the action vocabulary, one worked example per file kind, and common quirks (report lines above the header, footers, timestamps, separate reply rows).

**`references/metric-definitions.md`:** each metric from spec section 7.2 in plain language, why it matters, and how targets work.

**`references/coaching-playbook.md`:** for each step and for stretch focus, the causes to explore, checks to run, practice ideas, and questions. Include the language rules from spec section 9.4 and section 12.

**`README.md`:** what it does, requirements, install with `claude --plugin-dir`, a five-minute sample walkthrough, the weekly routine, privacy (including that anything Claude reads is handled under the manager's Claude plan), target sources, tested platforms, and the fact that sample data is fake.

- [ ] **Step 4: Run the tests and confirm they pass**
- [ ] **Step 5: Commit** with message `docs: add skills, coaching playbook, and README`

### Task 11: Final verification

**Files:**
- Modify: anything the checks below reveal, and `docs/superpowers/specs/2026-10-30-sdr-manager-design.md` (`Status` line)

- [ ] **Step 1: Run tests on both Python versions and measure coverage**

```bash
python3 -m unittest discover -s tests -t .
/usr/bin/python3 -m unittest discover -s tests -t .
.venv/bin/coverage run --source=scripts -m unittest discover -s tests -t .
.venv/bin/coverage report --fail-under=80
```

Expected: all pass, coverage at least 80%.

- [ ] **Step 2: Validate the plugin**

```bash
claude plugin validate .
```

- [ ] **Step 3: Run a real end-to-end session against the sample**

Use the cheapest model, in a scratch folder, with the plugin loaded for this session only. Record the elapsed time for success criterion 1.

```bash
claude -p --plugin-dir /path/to/sdr-plugin --model haiku --allowedTools "Bash(python3:*),Read,Write,Edit,Glob,Grep" "Run /sdr-manager:setup with the sample team, then /sdr-manager:scorecard for 2026-W44. Accept your own proposed column mappings and assume no time off."
claude -p --plugin-dir /path/to/sdr-plugin --model haiku --allowedTools "Bash(python3:*),Read,Write,Edit,Glob,Grep" "Run /sdr-manager:one-on-one for Chloe Nguyen with no extra notes."
```

Expected: the team report and 1:1 PDFs exist, and every sample rep has the expected status in the metrics file.

- [ ] **Step 4: Test the 1:1 loop**

Log an entry with `log-coaching`, run the 1:1 prep for that rep again, and confirm the saved commitment appears in the new PDF.

- [ ] **Step 5: Check both PDFs by eye**

Open them with the Read tool. Check for page overflow, unclear status, broken tables, and grayscale readability.

- [ ] **Step 6: Review the code with one agent**

Run one `python-reviewer` agent on the Sonnet model across `scripts/`, with a security focus on file handling and HTML escaping. Fix any CRITICAL or HIGH findings and re-run the tests.

- [ ] **Step 7: Check the success criteria**

Confirm each of the six criteria in spec section 14 with evidence, and list anything not met.

- [ ] **Step 8: Commit** with message `chore: verify first build end to end`

---

## Not included in this plan

- Publishing to GitHub or a marketplace, and choosing a license. This needs its own approval.
- A logo or brand colors. Only the brand name has been supplied, and teams can't yet set their own.
- Testing on Windows, Linux, or Cowork. The README states what was tested.
- Stages 2 to 4 from the spec.

## Changes made during the build

The tasks above are the original plan. These changes came out of building and testing it:

- **Tools:** the user's Python rules call for `pytest`, `ruff`, `black`, `isort`, and `bandit`, so they joined `coverage` in `.venv`. Tests stay in `unittest` form, so they still run with no installs.
- **Inspection:** `inspect` finds the real header row by itself, so report lines above it can't push prospect details past the masking.
- **Mappings:** added the `skip` action for notes and tasks, and the `any` flag for columns such as `Replied At` timestamps.
- **Reports:** targets show their exact value, so 3.41% against 3.43% can't read as 3.4% against 3.4%. The 1:1 page gained the five steps and a notes area.
- **Statistics rule:** a real Haiku session wrote numbers that were real but attached to the wrong period, which the original check allowed. Claude's text now states no statistics, the calculator writes the 1:1's wins and evidence, and `check-narrative` no longer takes `--week`. See spec section 10.
- **Chat summary:** `metrics` now returns `focus_text` and `status_counts`, so the summary can repeat exact wording.
