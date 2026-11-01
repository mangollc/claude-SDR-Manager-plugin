---
name: setup
description: This skill should be used when an SDR manager says "set up SDR Manager for my team", "set up SDR Manager with the sample team", "add my team", "add a rep", "a rep left", "change a target", "update our targets", "add a proof point", "change the name on our reports", or "try the sample team". It creates or updates the team's folder and profile.
argument-hint: "[sample]"
---

# Set up an SDR team

Help a sales manager get ready to use this plugin.

Talk to the manager in everyday words, because they may not be technical. Say "your team's folder", not "workspace", and "your files", not "exports" or "mappings". Don't show commands, code, JSON, or folder structures unless they ask. When you suggest a next step, give them a sentence to type.

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

**Sample path:** run `init-workspace --path sdr-demo --sample`. Tell the manager the sample is a made-up team of seven reps, then suggest they say "Run my SDR scorecard." Stop here.

**Real team:** ask where to keep the team's data. The default is `sdr-workspace` in the current folder. Run `init-workspace --path <folder>`, then use the full `path` from the result for every later command and every file you save.

If the result says `already_exists: true`, this is an update. Read `team-profile.json`, ask what changed, and change only that. Never replace an existing profile.

## Step 3: Learn about the team

Ask in small batches, and don't ask for anything the manager already told you:

1. The company and product, in a sentence or two
2. "What name should go on your reports?" Most teams use their company name, so offer that
3. The ideal customer
4. Each rep's name and start date, plus any other spelling of their name used in sales tools
5. Which channels the team uses: calls, email, LinkedIn
6. Anyone who appears in exports but isn't a rep, such as the manager
7. Any true results or customer names reps may mention in their outreach, which sales teams call proof points. It's fine if there are none

Save the answers to `team-profile.json` in that folder:

```json
{
  "company": "Example Analytics",
  "brand": "Example Analytics",
  "product": "Forecasting software for retailers",
  "ideal_customer": "Operations leaders at mid-size retailers",
  "proof_points": ["Northwind Stores cut stockouts by 18% in its first year."],
  "channels": ["call", "email", "linkedin"],
  "reps": [
    {"name": "Ava Reyes", "start_date": "2025-02-03", "aliases": ["A. Reyes"], "active": true}
  ],
  "ignored_names": ["Morgan Lee"],
  "targets": {}
}
```

Save the report name under `brand`, spelled exactly as the manager wants it, in up to 60 characters. Use the company name if they have no preference. If they ask to change it later, change only `brand`.

Use `YYYY-MM-DD` for dates. When a rep leaves, set `active` to `false` instead of deleting them. If a start date is unknown, leave it blank and say that the rep will be treated as fully ramped. Save `proof_points` as a list of short sentences, or as an empty list if there are none, so the manager isn't asked again.

## Step 4: Agree the targets

Run `targets --workspace <folder>`. This also confirms the profile is valid.

Show the targets in a simple table with their sources. Explain that they're published averages, so on target means typical, not excellent. Point out that the show rate comes from the oldest source, and that a team's own numbers are always better.

If the manager wants to replace a target, add it under `targets`, using the key from the command's output. Rates are decimals, so 8% is `0.08`:

```json
{"targets": {"connect_rate": {"value": 0.08, "as_of": "2026-10-30"}}}
```

Leave `meeting_rate` alone unless the team has its own number, because the plugin calculates it from the other targets. Run `targets` again to confirm.

If the manager wants a different length limit for rewritten messages, add it under `outreach_limits`, using `first_email`, `follow_up_email`, `call_script`, `linkedin_note`, or `linkedin_message`. A team with LinkedIn Premium may want 300 for `linkedin_note`:

```json
{"outreach_limits": {"linkedin_note": {"value": 300, "as_of": "2026-10-30"}}}
```

## Step 5: Finish

Tell the manager:

- Coaching notes and downloaded files are sensitive, so keep this folder out of shared drives.
- Each team needs its own folder.
- The next step is to say "Run my SDR scorecard."
