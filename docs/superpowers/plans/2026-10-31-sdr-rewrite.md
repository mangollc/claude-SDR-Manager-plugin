# sdr-rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task, inline. Inline is the recommended route because the user's token-budget rule prefers inline work on Opus. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a command that rewrites one email, cold call script, or LinkedIn message, then checks the result and saves it only if it passes.

**Architecture:** A new skill holds the judgment and a new `outreach.py` module holds the checks. Claude writes `outreach/draft.json`, `check-outreach` rejects or saves it, and team facts come from `team-profile.json`.

**Tech Stack:** Python 3.9+ standard library, `unittest`, Markdown skills.

**Spec:** `docs/superpowers/specs/2026-10-31-sdr-rewrite-design.md`

## Global Constraints

- Runtime is Python 3.9 or newer, standard library only.
- Add `from __future__ import annotations` to every Python module.
- Tests use `unittest`, and must pass on `python3` and `/usr/bin/python3` (3.9.6).
- Coverage of `scripts/` stays at 80% or higher.
- Every command prints JSON. Exit codes: 0 success, 1 unexpected error, 2 the manager or Claude must fix something, 3 Python too old.
- Skills reference bundled files with `${CLAUDE_PLUGIN_ROOT}`. No fixed paths.
- Claude never sends messages or changes anything in a sales tool.
- Functions stay under 50 lines and files under 800. Functions return new objects and don't mutate their inputs.
- Everything managers see stays in everyday words, and skills give a sentence to type.
- Git: commit to `main`, as the owner asked for one branch, using `<type>: <description>`. No attribution lines, because the user's git rule disables them.

## How to read this plan

As in the first build, each task gives exact interfaces, test cases, and expected values. Full source listings are left out, because writing every line here and again in the code would spend the user's usage limit twice. Test cases are requirements: each becomes a real test, written before its implementation.

Standard test command:

```bash
python3 -m unittest discover -s tests -t .
```

## File structure

```text
assets/outreach-limits.json        starting limits, with sources
references/outreach-playbook.md    what good looks like per channel, with dated sources
sample-data/outreach/              three deliberately weak messages
scripts/sdrlib/outreach.py         the checks and the saved file
skills/rewrite/SKILL.md            the manager's experience
tests/test_outreach.py             every rule, passing and failing
```

---

### Task 1: Team profile fields

**Files:**
- Modify: `scripts/sdrlib/profile.py`, `tests/test_profile.py`

**Interfaces:**
- Produces: `load_profile` raises `ProfileError` for bad `proof_points` or `outreach_limits`. A missing `proof_points` key is valid, and means the team hasn't been asked yet.

- [ ] **Step 1: Write failing tests:** `proof_points` as text rather than a list, a list holding a blank or a number, `outreach_limits` that isn't an object, a limit of zero, a negative limit, a limit of `true`, and valid values that load.
- [ ] **Step 2: Run them.** Expected: FAIL, because nothing validates these fields.
- [ ] **Step 3: Add `_validate_outreach(profile)` and call it from `_validate`.**
- [ ] **Step 4: Run the tests.** Expected: PASS.

### Task 2: Limits and checks

**Files:**
- Create: `assets/outreach-limits.json`, `scripts/sdrlib/outreach.py`, `tests/test_outreach.py`

**Interfaces:**
- Consumes: `check_narrative` and `extract_number_words` from `narrative_check.py`, `ASSETS_DIR` from `targets.py`.
- Produces:
  - `KINDS`: `first_email`, `follow_up_email`, `call_script`, `linkedin_note`, `linkedin_message`
  - `resolve_limits(team: dict) -> dict`: starting limits with team overrides, each override showing `source: "team"`
  - `find_placeholders(text: str) -> set[str]`
  - `protected_text(original: str) -> list[str]`
  - `check_draft(draft: dict, team: dict) -> dict` with `problems`, `to_confirm`, and `length`

- [ ] **Step 1: Write failing tests**, one class per rule:

| Rule | Test cases |
|---|---|
| Limits | Each kind has a positive limit and a source. Values are 80, 125, 150, 200 characters, and 100. A team override wins and shows `source: "team"`. An unknown kind raises `ValueError` |
| Placeholders | Finds `{{first_name}}`, `{{ contact.firstname }}`, `{{first_name\|there}}`, `{{{Recipient.FirstName}}}`, `{!Contact.FirstName}`, `[[Company]]`, `[Company]`, `<<Company>>`, and `%first_name%`. Rejects a changed spelling, a dropped one, and a new one. New ones go to `to_confirm` when the original has none. One moved to the footer still counts |
| Protected text | Rejects a dropped or reworded opt-out, address, or recording notice. Finds an opt-out inside a paragraph, and requires only that sentence. Ignores line wrapping. Protects a P.O. Box. "Our call recording software" isn't protected |
| New numbers | Rejects `40%`, `10x`, and `$2M`. Allows numbers from the original, profile, and proof points. Allows `15-minute`, `30 minutes`, `2pm`, and `10:30`. Ignores `B2B`, `Q3`, and digits inside placeholders |
| Length | Rejects 81 words for a first email, and passes 80. Ignores the footer. Counts characters for a LinkedIn note. Uses a team override. Reports `value`, `limit`, `unit`, and `source` |
| First contact | Rejects `Re:`, `Fwd:`, and `FW:` subjects on a first email, and allows them on a follow-up. Rejects "as we discussed" in a first email, note, or call script, and allows it in a follow-up |
| Why it changed | Rejects a statistic and a gendered pronoun in `changes` |
| Confirm | Lists a new name and groups "Acme Corp". Leaves out approved names, days, months, "I", and first words of sentences. Lists spelled-out numbers and "doubled". Lists a missing opt-out and address for email only. A `{{signature}}` or `{{unsubscribe_link}}` placeholder clears both. Every item has a `message` |
| Bad drafts | An unknown `kind`, a missing or blank `name`, `original`, or `body`, and a non-text `subject`, `footer`, or `changes` all raise `ValueError` with a plain message |

- [ ] **Step 2: Run them.** Expected: FAIL with `ImportError`.
- [ ] **Step 3: Implement**, using this number logic, which is the easiest part to get wrong:

```python
NUMBER = re.compile(r"(?<![A-Za-z0-9.])\d[\d,]*(?:\.\d+)?")

def _numbers(text: str) -> set[str]:
    spare = MEETING_TIME.sub(" ", PLACEHOLDER.sub(" ", text))
    return {token.replace(",", "") for token in NUMBER.findall(spare)}
```

- [ ] **Step 4: Run the tests.** Expected: PASS.

### Task 3: Save file and command

**Files:**
- Modify: `scripts/sdrlib/outreach.py`, `scripts/sdr.py`, `tests/test_outreach.py`

**Interfaces:**
- Produces:
  - `load_draft(path: Path) -> dict`, raising `ValueError` with a plain message
  - `render_saved(draft: dict, confirm: list, day: date) -> str`
  - `save_rewrite(workspace: Path, draft: dict, confirm: list, day: date) -> Path`
  - `check-outreach --workspace W --draft F`

- [ ] **Step 1: Write failing tests:**
  - The saved layout matches section 8 of the spec.
  - A call script has no subject line.
  - The saved file leaves out the original.
  - The same name on the same day replaces the file.
  - An older workspace gets an `outreach` folder.
  - A passing command exits 0, saves the file, deletes the draft, and prints `path`, `length`, and `to_confirm`.
  - A failing command exits 2, saves nothing, and keeps the draft.
  - A missing draft, invalid JSON, and a JSON list exit 2 with a plain message.
  - Proof points in the team's profile allow their numbers.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement, and add the command to `COMMANDS`.**
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** tasks 1 to 3: `feat: check rewritten outreach before saving it`.

### Task 4: Skill, playbook, samples, and installer

**Files:**
- Create: `skills/rewrite/SKILL.md`, `references/outreach-playbook.md`, `sample-data/outreach/weak-email.txt`, `weak-call-script.txt`, `weak-linkedin-note.txt`
- Modify: `install.py`, `tests/make_sample_data.py`, `sample-data/team-profile.json`, `tests/test_plugin_files.py`, `tests/test_installer.py`, `tests/test_outreach.py`

- [ ] **Step 1: Write failing tests:**
  - `rewrite` joins the skill lists in both test files, so every existing skill rule applies to it.
  - The skill recognizes "rewrite this email", "rewrite this call script", "rewrite this linkedin message", "rewrite our first email", and "rewrite the sample email".
  - `outreach-playbook.md` exists and a skill uses it.
  - The skill forbids invented facts, forbids legal advice, and asks about proof points only when the key is missing.
  - The installer writes `sdr-rewrite`, and its sample messages reach the program folder.
  - Each sample message fails the checks if used unchanged: the email for `too_long`, `fake_reply`, and `false_history`, the note for `too_long`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Write the files, and add `rewrite` to `SKILLS` in `install.py`.** The samples use only made-up facts.
- [ ] **Step 4: Run the tests.** Expected: PASS.

### Task 5: Setup and scorecard

**Files:**
- Modify: `skills/setup/SKILL.md`, `skills/scorecard/SKILL.md`, `tests/test_plugin_files.py`

- [ ] **Step 1: Write failing tests:** setup asks about proof points and shows `outreach_limits`, and the scorecard suggests "Rewrite our first email."
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Edit both skills.** Setup saves an empty list when there are no proof points. The scorecard suggests a rewrite when `team_pattern` has `step` 2 or 3.
- [ ] **Step 4: Run the tests.** Expected: PASS.

### Task 6: Guides and version

**Files:**
- Modify: `README.md`, `docs/technical-guide.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `tests/test_plugin_files.py`

- [ ] **Step 1: Write failing tests:** the README documents `/sdr-rewrite`, says the checks aren't legal advice, and says rewrites were tested on made-up messages only. The technical guide lists `check-outreach` and `sdr-rewrite`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Update both guides.** Cover the command table, an example, what's checked, the starting limits, privacy, test status, customizing, and the roadmap. Raise the version to 0.2.0.
- [ ] **Step 4: Run the tests.** Expected: PASS.
- [ ] **Step 5: Commit** tasks 4 to 6: `feat: add the rewrite command`.

### Task 7: Real sessions

- [ ] **Step 1: Install to a throwaway folder** with `install.py --skills-dir <folder>/.claude/skills --home <home>`, so the real install isn't touched.
- [ ] **Step 2: Run the README's sentences** on Haiku across all three channels, including the traps in section 11 of the spec.
- [ ] **Step 3: Check each saved file by program:** placeholders, protected text, new numbers, and limits.
- [ ] **Step 4: Read each transcript** for everyday words, gendered pronouns, and the number of questions asked.
- [ ] **Step 5: Fix what fails, and add a test for each fix.** Prefer a program rule when a skill rule was skipped.

### Task 8: Review and publish

- [ ] **Step 1: Run 3 Sonnet reviewers:** the checks, the skill and guides, and privacy and safety. Verify each finding before acting on it.
- [ ] **Step 2: Fix confirmed findings, with tests.**
- [ ] **Step 3: Run every check, then publish only if all pass:**

```bash
python3 -m unittest discover -s tests -t . && /usr/bin/python3 -m unittest discover -s tests -t . && .venv/bin/pytest -q --cov --cov-report=term && .venv/bin/ruff check install.py scripts tests && .venv/bin/black --check -q install.py scripts tests && .venv/bin/isort --check -q install.py scripts tests && .venv/bin/bandit -q -r scripts install.py && claude plugin validate . && git push origin main
```

- [ ] **Step 4: Update the owner's own install**, using the documented route, so `/sdr-rewrite` appears for them.
