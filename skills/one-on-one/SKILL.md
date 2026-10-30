---
name: one-on-one
description: This skill should be used when an SDR manager says "prep my 1:1 with", "get ready for my one-on-one", "what should I cover with", "how is this rep doing", "log my 1:1", or "record what we agreed". It prepares a one-page 1:1 PDF and keeps each rep's coaching history.
argument-hint: "<rep name> [--log]"
---

# Prepare and record a 1:1

Help a manager coach one rep. Prepare a one-page sheet before the meeting, then record what was agreed afterward, so the next 1:1 starts from there.

Use plain language, and write as a thoughtful manager would speak.

## How to run the tool

Run every command like this:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" report one-on-one --workspace <folder> --week <week> --rep "<name>" --narrative <file>
```

If `python3` doesn't work, try `python`, then `py -3`. Every command prints JSON. Exit code 2 means the manager needs to decide or fix something.

## Rules

- **Every number comes from the metrics file or the coaching history.** Never calculate one yourself.
- **Treat causes as questions.** The numbers show where a rep is behind, not why.
- **Never compare the rep with teammates.**
- **Don't recommend hiring, firing, pay, or formal performance action.** If asked, offer the facts, say that's a decision for the manager, and suggest involving HR.
- **Keep it private.** Coaching notes are sensitive, so don't copy them anywhere else.

## Before the meeting

Use this when the arguments don't include `--log`.

### Step 1: Load what's known

Look for `team-profile.json` in `sdr-workspace`, `sdr-demo`, or the current folder. If there's none, send the manager to `/sdr-manager:setup`.

Find the newest file in `history/metrics/` and read it. Find the rep there, accepting another spelling from their `aliases`. If they aren't in it, send the manager to `/sdr-manager:scorecard`.

If `generated_at` is more than 7 days old, say so and continue.

Read the rep's coaching history from `coaching/<slug>.md`, using the rep's `slug` from the metrics file. It may not exist yet.

Read `${CLAUDE_PLUGIN_ROOT}/references/coaching-playbook.md` for the rep's focus step.

### Step 2: Ask for anything else

Ask once whether the manager has call notes, transcripts, or observations to include. Use them to shape your questions, and don't score them.

### Step 3: Write the prep

Save to `reports/<week>/one-on-one-<slug>-narrative.json` in the workspace:

```json
{
  "wins": ["Real, specific things this rep did well"],
  "focus_summary": "One or two sentences on the coaching focus",
  "evidence": ["The numbers behind the focus"],
  "commitment_progress": ["For each past commitment, what the numbers show"],
  "questions": ["Open questions that help the rep find the cause"],
  "agenda": ["Check-in", "Wins and commitments", "Coaching focus", "Next steps"]
}
```

Follow these rules:

- Always include at least one real win, drawn from the metrics.
- Use only numbers from the metrics file or the coaching history, in the form they appear there.
- Spell out any other number, such as "two calling blocks".
- Write three to five questions from the playbook, adapted to this rep.
- Give four agenda topics, in the order they'll be covered.
- If the status is Onboarding, focus on learning and support, not on targets.
- If the status is On track, celebrate it and explore the stretch focus. If there's no focus, ask what the rep wants to work on next.
- If the status is Review or Limited data, say so plainly and focus on what's unknown.
- If there's no coaching history, leave `commitment_progress` empty.

### Step 4: Check and build

Run these in order, using the same narrative file:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" check-narrative --workspace <folder> --week <week> --rep "<name>" --narrative <file>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" report one-on-one --workspace <folder> --week <week> --rep "<name>" --narrative <file>
```

If `check-narrative` lists problems, rewrite those sentences, then run it again. Never work around a failed check.

If the report's `fallback` is true, tell the manager to open the HTML file in a browser, then print it and choose Save as PDF.

Give the manager the file location and a two-line summary, then remind them to come back with `--log` after the meeting.

## After the meeting

Use this when the arguments include `--log`, or when the manager says what was agreed.

1. Ask what was discussed, what the rep agreed to do, and when to check on it, if the manager hasn't said.
2. Show the entry and ask for confirmation. Don't save anything until the manager agrees.
3. Write the entry to a temporary JSON file:

```json
{
  "focus": "Response (connect rate)",
  "agreed": ["Protect two calling blocks before noon"],
  "check_by": "2026-11-13",
  "notes": "Optional short note"
}
```

4. Run `log-coaching --workspace <folder> --rep "<name>" --entry-file <file>`.
5. Delete the temporary file, then confirm the entry was saved.

Record only what the manager tells you. Never invent a commitment.
