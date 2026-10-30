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

- **Never write a statistic.** The page shows every number itself, so your text carries judgment only. Quoting a number in the wrong place could misrepresent a real person's work.
- **Treat causes as questions.** The numbers show where a rep is behind, not why.
- **Never compare the rep with teammates.**
- **Refer to the rep by name or as "they".** Never guess anyone's gender from a name.
- **Don't recommend hiring, firing, pay, or formal performance action.** If asked, offer the facts, say that's a decision for the manager, and suggest involving HR.
- **Keep it private.** Coaching notes are sensitive, so don't copy them anywhere else.

## Find the workspace

Do this first, before or after the meeting.

Run `status` from the manager's folder. Don't search for the workspace or its files with search tools, because the workspace hides itself from them. Use the `workspace` path in the output for every later command.

- If `status` exits with code 2, send the manager to `/sdr-manager:setup`.
- If `other_workspaces` isn't empty, check that this rep is in the workspace you're using. If not, look in the others with `status --workspace <folder>`, and say which one you're using.

## Before the meeting

Use this when the arguments don't include `--log`.

### Step 1: Load what's known

- If `latest_week` is null, send the manager to `/sdr-manager:scorecard`.
- If `metrics_age_days` is more than 7, say so and continue.

Read the file at `metrics_path`. Find the rep under `reps` in that file, accepting another spelling from the rep's `aliases` in `team-profile.json`. If they aren't there, send the manager to `/sdr-manager:scorecard`.

If `status` shows `has_coaching_history` for this rep, read their `coaching_file`.

Read `${CLAUDE_PLUGIN_ROOT}/references/coaching-playbook.md` for the rep's focus step.

### Step 2: Ask for anything else

Ask once whether the manager has call notes, transcripts, or observations to include. Use them to shape your questions, and don't score them.

### Step 3: Write the prep

Save to `reports/<week>/one-on-one-<slug>-narrative.json` in the workspace:

```json
{
  "wins": ["Up to three things the numbers can't show, in words"],
  "focus_summary": "One or two sentences on why this focus matters now",
  "commitment_progress": ["For each past commitment, whether things moved the right way"],
  "questions": ["Open questions that help the rep find the cause"],
  "agenda": ["Check-in", "Wins and commitments", "Coaching focus", "Next steps"]
}
```

The page adds the numbers itself: every on-target step is listed as a win, and the focus metric and its weekly values are listed as evidence. So don't repeat those. Leave `wins` empty if you have nothing to add, and keep every sentence short, because the page has to fit on one sheet.

Follow these rules:

- **Write no numbers in `wins`, `focus_summary`, or `commitment_progress`, in digits or in words.** The only exception is a number from the rep's coaching history, such as an agreed "50 dials".
- `questions` and `agenda` may use words like "two calling blocks", but no digits.
- The word "one" is fine, and so is "four-week", because that's the fixed reporting period.
- Only describe what the metrics file shows. Base every claim on a status or a step.
- Write three to five short questions from the playbook, adapted to this rep.
- Give four agenda topics, in the order they'll be covered.
- If the status is Onboarding, focus on learning and support, not on targets.
- If the status is On track, celebrate it and explore the stretch focus. If there's no focus, ask what the rep wants to work on next.
- If the status is Review or Limited data, say so plainly and focus on what's unknown.
- If there's no coaching history, leave `commitment_progress` empty.

### Step 4: Check and build

Run these in order, using the same narrative file:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" check-narrative --workspace <folder> --rep "<name>" --narrative <file>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" report one-on-one --workspace <folder> --week <week> --rep "<name>" --narrative <file>
```

If `check-narrative` lists problems, fix each one and run it again. For a `statistic`, remove the number and say the same thing in words. For a `pronoun`, use the rep's name or "they". Never work around a failed check.

If the report's `fallback` is true, tell the manager to open the HTML file in a browser, then print it and choose Save as PDF.

Give the manager the file location and a two-line summary, then remind them to come back with `--log` after the meeting.

## After the meeting

Use this when the arguments include `--log`, or when the manager says what was agreed.

1. Ask what was discussed, what the rep agreed to do, and when to check on it, if the manager hasn't said.
2. Show the entry and ask for confirmation, unless the manager has already confirmed it. Don't save anything until the manager agrees.
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
