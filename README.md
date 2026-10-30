# sdr-manager

A Claude plugin for SDR managers. It turns your team's sales exports into a weekly scorecard, gives each rep one clear coaching focus, and prepares and records your 1:1s.

Reports are branded Andy Gheewalla.

## What it does

| Command | When | What you get |
|---|---|---|
| `/sdr-manager:setup` | Once | A team profile with your product, ideal customer, reps, and targets |
| `/sdr-manager:scorecard` | Weekly | A PDF with a team summary and one page per rep |
| `/sdr-manager:one-on-one` | Around each 1:1 | A one-page prep sheet, then a saved record of what was agreed |

The scorecard follows every rep through five steps: activity, response, meetings booked, meetings held, and meetings accepted. The first step behind target becomes that rep's coaching focus.

It works with outbound email, cold calls, and LinkedIn. It reads CSV or Excel exports from any sales tool.

## Requirements

- Claude Code
- Python 3.9 or newer
- Chrome, Edge, Chromium, or Brave to create PDFs. Without one, you get a web page you can save as a PDF from any browser
- Optional: the `openpyxl` Python package to read Excel files directly. Without it, save Excel files as CSV

Setup checks all of this for you.

## Install

Load the plugin for a session:

```bash
claude --plugin-dir /path/to/sdr-plugin
```

## Try it with sample data

The plugin includes a made-up team of seven reps, each showing a different situation. All names, companies, and numbers are fake.

1. Run `/sdr-manager:setup sample`.
2. Run `/sdr-manager:scorecard`, and confirm how the sample columns are read.
3. Run `/sdr-manager:one-on-one Chloe Nguyen`.

## Your weekly routine

1. Export the week's activity from each channel, plus a meetings report from your CRM.
2. Run `/sdr-manager:scorecard`, and read the PDF.
3. Before each 1:1, run `/sdr-manager:one-on-one <rep>`.
4. After each 1:1, run `/sdr-manager:one-on-one <rep> --log`.

The first run takes longer, because you confirm what your columns mean. After that, the plugin remembers.

## How your data is handled

Privacy matters here, because this plugin touches both employee performance and prospect details.

- The plugin has no server and sends nothing anywhere itself.
- Anything Claude reads is handled under the terms of your Claude plan.
- Claude sees column names and a masked preview of each export, not the full file. Scripts read the full file on your computer.
- Stored history holds counts and rep names. Prospect names, emails, phone numbers, and companies are not kept.
- Exports you leave in the workspace's `imports` folder stay there until you delete them.
- Coaching notes are plain text files on your computer. Keep the workspace out of shared folders. It's set up so Git ignores it.

## What Claude won't do

- Send messages or change anything in your sales tools
- Rank reps against each other
- Recommend hiring, firing, pay, or formal performance action
- Write statistics into a report. The calculator produces every number, and a check blocks any report where Claude's text states one of its own. The one exception is a number from your own coaching notes, such as an agreed "50 dials"

## Targets

Starting targets are published figures, and each one is listed with its source on the report's final page. They come from The Bridge Group, Gong Labs, Instantly, Expandi, and Operatix.

Most sources are vendors reporting their own data, and definitions vary. On target means typical, not excellent. Replace them with your own numbers as soon as you can.

## What's tested

Tested on macOS with Claude Code, Python 3.9 and 3.12, and Chrome. Windows, Linux, and Cowork haven't been tested yet.

To run the tests:

```bash
python3 -m unittest discover -s tests -t .
```

## Not included yet

- Inbound leads
- Cadence audits and rewriting outreach
- Onboarding plans, role-play, and call scoring
- Leadership slides and capacity planning
- Live connections to sales tools
