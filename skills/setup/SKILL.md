---
name: setup
description: This skill should be used when an SDR manager says "set up sdr-manager", "add my team", "add a rep", "a rep left", "change a target", "update our targets", or "try the sample team". It creates or updates the team's workspace and profile.
argument-hint: "[sample]"
---

# Set up an SDR team

Help a sales manager get ready to use this plugin. Use plain language, and don't show JSON or folder structures unless asked.

## How to run the tool

Run every command like this:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sdr.py" check-env
```

If `python3` doesn't work, try `python`, then `py -3`, and keep using whichever works. Every command prints JSON. Exit code 2 means the manager needs to decide or fix something, and the output says what.

## Step 1: Check the computer

Run `check-env`, then act on the result:

- **Python is missing or older than 3.9:** stop and give these steps.
  - macOS: download the installer from python.org/downloads, run it, then restart Claude.
  - Windows: do the same, and tick **Add python.exe to PATH** on the first installer screen.
- **`browser` is null:** continue. Explain that reports will arrive as a web page the manager can open and save as a PDF.
- **`openpyxl` is false:** continue. Explain that Excel files need saving as CSV first.

## Step 2: Choose a path

If the arguments say `sample`, or the manager wants to try the plugin first, use the sample path. Otherwise ask which they'd like.

**Sample path:** run `init-workspace --path sdr-demo --sample`. Tell the manager the sample is a made-up team of seven reps, then suggest `/sdr-manager:scorecard`. Stop here.

**Real team:** ask where to keep the team's data. The default is `sdr-workspace` in the current folder. Run `init-workspace --path <folder>`.

If the result says `already_exists: true`, this is an update. Read `team-profile.json`, ask what changed, and change only that. Never replace an existing profile.

## Step 3: Learn about the team

Ask in small batches, and don't ask for anything the manager already told you:

1. The company and product, in a sentence or two
2. The ideal customer
3. Each rep's name and start date, plus any other spelling of their name used in sales tools
4. Which channels the team uses: calls, email, LinkedIn
5. Anyone who appears in exports but isn't a rep, such as the manager

Save the answers to `team-profile.json`:

```json
{
  "company": "Example Analytics",
  "product": "Forecasting software for retailers",
  "ideal_customer": "Operations leaders at mid-size retailers",
  "channels": ["call", "email", "linkedin"],
  "reps": [
    {"name": "Ava Reyes", "start_date": "2025-02-03", "aliases": ["A. Reyes"], "active": true}
  ],
  "ignored_names": ["Morgan Lee"],
  "targets": {}
}
```

Use `YYYY-MM-DD` for dates. When a rep leaves, set `active` to `false` instead of deleting them. If a start date is unknown, leave it blank and say that the rep will be treated as fully ramped.

## Step 4: Agree the targets

Run `targets --workspace <folder>`. This also confirms the profile is valid.

Show the targets in a simple table with their sources. Explain that they're published averages, so on target means typical, not excellent. Point out that the show rate comes from the oldest source, and that a team's own numbers are always better.

If the manager wants to replace a target, add it under `targets`, using the key from the command's output. Rates are decimals, so 8% is `0.08`:

```json
{"targets": {"connect_rate": {"value": 0.08, "as_of": "2026-10-30"}}}
```

Leave `meeting_rate` alone unless the team has its own number, because the plugin calculates it from the other targets. Run `targets` again to confirm.

## Step 5: Finish

Tell the manager:

- Coaching notes and exports are sensitive, so keep this folder out of shared drives.
- Each team needs its own workspace.
- The next step is `/sdr-manager:scorecard`.
