---
name: scorecard
description: This skill should be used when an SDR manager says "run the scorecard", "build the weekly report", "how did my reps do this week", "analyze my team's numbers", "import these sales exports", or shares CSV or Excel exports of SDR activity. It turns exports into a team report PDF with one coaching focus per rep.
argument-hint: "[folder or files] [week, such as 2026-W44]"
---

# Build the weekly scorecard

Turn a team's sales exports into a PDF report. Scripts do all the math. Your job is to work out what the exports mean, confirm it with the manager, and write short, honest observations.

Use plain language. The manager may not be technical.

## How to run the tool

Run every command like this:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" inspect <file> --workspace <folder>
```

If `python3` doesn't work, try `python`, then `py -3`. Every command prints JSON. Exit code 2 means the manager needs to decide or fix something.

## Rules

- **Never open an export file directly.** Use `inspect`, which masks prospect details. Full exports only ever go through the scripts.
- **Never do the math yourself.** Every number comes from the metrics file.
- **Never rank reps** or compare them with each other in your text.
- **Treat causes as questions.** The numbers show where a rep is behind, not why.
- **Don't recommend hiring, firing, pay, or formal performance action.** If asked, offer the facts and suggest involving HR.
- **Never send anything or change anything in a sales tool.**

## Step 1: Find the workspace and exports

Look for `team-profile.json` in `sdr-workspace`, `sdr-demo`, or the current folder. If there's none, send the manager to `/sdr-manager:setup`.

Use any folder or files given as arguments. Otherwise look in `imports/<week>/` inside the workspace, then ask.

On a first run, ask for the last four full weeks plus the current week, so trends work from the start. Always ask for a meetings export that covers at least the last six weeks, because meeting statuses change after booking.

Explain what to export if the manager is unsure: activity from each channel, plus a meetings report from the CRM. Each channel must come from one file only, otherwise touches get counted twice.

## Step 2: Understand each file

Run `inspect <file> --workspace <folder>` for each file.

- If `matched_mapping` has a name, the file is already understood. Move on.
- If not, read `${CLAUDE_PLUGIN_ROOT}/references/file-mapping-guide.md` and work out a mapping. Use the `header_row` and `signature` from the output.

Explain each new mapping in plain language and ask the manager to confirm it. Name the choices that change the numbers:

> In the call file, I'm counting "Connected" as a live conversation. "Voicemail", "No Answer", and "Busy" count as dials without a connection. Does that match how your team works?

Save each confirmed mapping to `mappings/<short-name>.json` in the workspace.

## Step 3: Ask about time off

If `history/time-off/<week>.json` doesn't exist, ask about holidays and time off that week, then save it, even when the answer is none:

```json
{"team_days_off": 1, "rep_days_off": {"Ben Carter": 2}}
```

Do this for the selected week only, unless the manager mentions earlier weeks.

## Step 4: Store the numbers

Run `normalize --workspace <folder> --files <file> <file> --week <week>`. Leave out `--week` if the manager didn't choose one.

Nothing is stored unless every file passes. If `status` is `needs_input`, resolve each item and run it again:

| Field | What to do |
|---|---|
| `files_without_mapping` | Go back to step 2 |
| `unknown_reps` | Ask whether it's a new rep, another spelling of a known rep, or someone to ignore. Update `team-profile.json` |
| `unmapped_values` | Ask what the new value means, then add it to the mapping. Never guess |
| `channel_conflicts` | Ask which file to use for that channel, and leave the other out |
| `too_many_rejected` | Show `rejected_examples` and ask how to proceed. The header row or date format may be wrong |

## Step 5: Calculate

Run `metrics --workspace <folder> --week <week>`, leaving out `--week` to use the latest week with data.

Read the file at `path`. Also read `${CLAUDE_PLUGIN_ROOT}/references/coaching-playbook.md`, and `${CLAUDE_PLUGIN_ROOT}/references/metric-definitions.md` if the manager asks what a number means.

## Step 6: Write the observations

Save to `reports/<week>/team-narrative.json` in the workspace:

```json
{
  "headline": "One sentence on the team's week",
  "observations": ["At most three short points"],
  "rep_notes": {"Ava Reyes": "One short coaching idea, phrased as something to explore"}
}
```

Follow these rules:

- Use only numbers from the metrics file, in the form they appear on the report.
- Spell out any other number, such as "four-week".
- Don't calculate differences or new percentages.
- Lead with what the manager should do, not what the numbers are.
- If `team.pattern` is set, mention it. A shared problem usually points to the list, messaging, or targets.
- If a rep has `bounce_warning`, suggest checking list quality before coaching on replies.
- If a rep is Onboarding, leave their note out.

## Step 7: Check the numbers and build the report

Run these in order:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" check-narrative --workspace <folder> --week <week> --narrative <file>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" report team --workspace <folder> --week <week> --narrative <file>
```

If `check-narrative` lists problems, rewrite those sentences using numbers from the metrics file, then run it again. Never work around a failed check.

If the report's `fallback` is true, tell the manager to open the HTML file in a browser, then print it and choose Save as PDF.

## Step 8: Summarize in chat

Keep it short:

1. The team's status, including how many reps are in each status
2. Who needs attention, with each rep's one focus
3. Any team pattern
4. Where the PDF is
5. Any data warnings, such as a partial week, missing channels, rejected rows, or missing meetings

Then suggest `/sdr-manager:one-on-one` for the rep who needs it most.
