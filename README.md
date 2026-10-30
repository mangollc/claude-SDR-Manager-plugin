# SDR Manager

**A coaching and reporting assistant for sales development managers.** It turns your team's sales exports into a weekly scorecard, gives each rep one clear coaching focus, and prepares and records your 1:1s.

It works in Claude Code, Codex, Cursor, VS Code Copilot, and other AI tools that support skills, on Mac and Windows.

No API keys. No environment variables. No external services. [See exactly what it uses](#external-services-api-keys-and-environment-variables).

```text
  Your sales exports            SDR Manager                  What you get
 ┌──────────────────┐      ┌──────────────────────┐      ┌────────────────────┐
 │ Calls            │      │ 1. Understands your  │      │ Team report PDF    │
 │ Emails           │ ───► │    columns           │ ───► │ One page per rep   │
 │ LinkedIn         │      │ 2. Calculates        │      │ One coaching focus │
 │ Meetings         │      │ 3. Finds each rep's  │      │ 1:1 prep sheet     │
 │ (CSV or Excel)   │      │    first weak step   │      │ Coaching history   │
 └──────────────────┘      └──────────────────────┘      └────────────────────┘
```

## Contents

- [What it is](#what-it-is)
- [External services, API keys, and environment variables](#external-services-api-keys-and-environment-variables)
- [Install](#install)
- [Try it with sample data](#try-it-with-sample-data)
- [Commands](#commands)
- [What the reports look like](#what-the-reports-look-like)
- [How the coaching focus works](#how-the-coaching-focus-works)
- [What to export from your sales tools](#what-to-export-from-your-sales-tools)
- [Your weekly routine](#your-weekly-routine)
- [Targets](#targets)
- [Privacy: how your data is handled](#privacy-how-your-data-is-handled)
- [Customizing](#customizing)
- [Troubleshooting](#troubleshooting)
- [What's tested](#whats-tested)
- [For developers](#for-developers)
- [Roadmap](#roadmap)
- [License](#license)

## What it is

SDRs, or sales development reps, make first contact with potential customers and book meetings for account executives (AEs). An SDR manager coaches those reps and reports on their results.

That job usually means hours in spreadsheets, trying to work out why a rep's numbers are down. SDR Manager does that part for you:

- **Weekly scorecard:** reads exports from any sales tool and produces a branded PDF.
- **One coaching focus per rep:** finds the first place each rep falls behind, so you know what to talk about.
- **1:1 prep:** builds a one-page sheet with wins, evidence, questions, and an agenda.
- **Coaching history:** records what each rep agreed to, so the next 1:1 starts from there.

It covers outbound email, cold calls, and LinkedIn. You don't need to be technical to use it, and it works with any CRM or outreach tool that can export a file.

Reports are branded Andy Gheewalla. See [Customizing](#customizing) to change that.

## External services, API keys, and environment variables

**SDR Manager needs none of these.** Its code was audited for network use before release.

| Question | Answer |
|---|---|
| API keys | **None** |
| Environment variables | **None** |
| External services or APIs | **None.** The program makes no network calls |
| Accounts to create | **None**, apart from the AI tool you already use |
| Paid services | **None** |
| Python packages to install | **None.** It uses Python's standard library |

**What it does use, all on your own computer:**

| Program | Why | Required? |
|---|---|---|
| Python 3.9 or newer | Does the calculations | Yes |
| Chrome, Edge, Chromium, or Brave | Turns reports into PDFs, working offline | Optional. Without one, you get a web page you can save as a PDF |
| `openpyxl` Python package | Reads Excel files directly | Optional. Without it, save Excel files as CSV |
| Your AI tool | Runs the skills and writes the coaching notes | Yes |

The AI tool is the one outside connection, because it's how you talk to the plugin. It sends what it reads to its own provider, under your plan's terms. See [Privacy: how your data is handled](#privacy-how-your-data-is-handled) for exactly what that includes.

## Install

### Requirements

- A Mac or Windows computer
- Python 3.9 or newer
- An AI tool: Claude Code, Codex, Cursor, VS Code with Copilot, or similar
- Optional: Chrome, Edge, Chromium, or Brave, to create PDFs

### Step 1: Check for Python

**Mac**

```bash
python3 --version
```

**Windows (PowerShell)**

```powershell
py -3 --version
```

You need version 3.9 or newer. If it's missing, install it from [python.org/downloads](https://www.python.org/downloads/). On Windows, tick **Add python.exe to PATH** on the first installer screen.

### Step 2: Install for your AI tool

#### Claude Code (Mac and Windows)

This is the recommended route for Claude Code. It installs globally, so it's available in every project.

```bash
claude plugin marketplace add mangollc/claude-SDR-Manager-plugin
claude plugin install sdr-manager@mango-plugins
```

Then start a new session. You can also run these from inside Claude Code by starting each with `/plugin` instead of `claude plugin`.

#### Codex, Cursor, VS Code Copilot, and Gemini CLI

One installer covers all of these, because they share one global skills folder.

**Mac**

```bash
git clone https://github.com/mangollc/claude-SDR-Manager-plugin.git
cd claude-SDR-Manager-plugin
python3 install.py
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/mangollc/claude-SDR-Manager-plugin.git
cd claude-SDR-Manager-plugin
py -3 install.py
```

No Git? Use **Code > Download ZIP** on this page, unzip it, and run the last line from inside that folder.

Then restart your AI tool. The installer doesn't touch your projects:

```text
 ~/.agents/skills/            The three skills your AI tools read
   sdr-setup/
   sdr-scorecard/
   sdr-one-on-one/
 ~/.sdr-manager/              The program behind them
```

On Windows, `~` means your user folder, such as `C:\Users\you`.

#### Which option for which tool?

| Tool | Command | Global folder |
|---|---|---|
| Claude Code | `claude plugin install` (above) | Managed by Claude Code |
| Claude Code, without the plugin | `install.py --tool claude` | `~/.claude/skills` |
| Codex | `install.py` | `~/.agents/skills` |
| Cursor | `install.py` | `~/.agents/skills` |
| VS Code with Copilot | `install.py` | `~/.agents/skills` |
| Gemini CLI | `install.py` | `~/.agents/skills` |
| Any other tool with a skills folder | `install.py --skills-dir <folder>` | The folder you name |

For a tool with no skills feature, install with `install.py` and tell it: *"Follow the instructions in `~/.agents/skills/sdr-scorecard/SKILL.md`."*

### Update or remove

| Task | Claude Code | Other tools |
|---|---|---|
| Update | `claude plugin update sdr-manager@mango-plugins` | `git pull`, then run `install.py` again |
| Remove | `claude plugin uninstall sdr-manager@mango-plugins` | `install.py --uninstall` |

Removing the plugin never touches your team's data.

## Try it with sample data

The plugin includes a made-up team of seven reps, each showing a different situation. All names, companies, and numbers are fake.

**In Claude Code:**

```text
/sdr-manager:setup sample
/sdr-manager:scorecard
/sdr-manager:one-on-one Chloe Nguyen
```

**In other tools,** ask in plain words:

```text
Set up SDR Manager with the sample team.
Run the SDR scorecard.
Prepare my 1:1 with Chloe Nguyen.
```

This takes about two minutes. You'll confirm how the sample columns are read, then get a PDF report.

| Sample rep | Situation | What the plugin finds |
|---|---|---|
| Ava Reyes | Healthy performer | On track, with a stretch goal |
| Ben Carter | Not enough outreach | Step 1: Activity |
| Chloe Nguyen | Busy, but few replies | Step 2: Response, plus a bounce warning |
| Diego Marin | Good replies, few meetings | Step 3: Meetings booked |
| Priya Shah | Many no-shows | Step 4: Meetings held |
| Sam Okafor | AEs reject the meetings | Step 5: Meetings accepted |
| Nina Patel | New hire | Onboarding, with no judgment |

## Commands

There are three. The names differ slightly by tool:

| Purpose | Claude Code plugin | Other tools |
|---|---|---|
| Set up your team | `/sdr-manager:setup` | `sdr-setup` |
| Build the weekly report | `/sdr-manager:scorecard` | `sdr-scorecard` |
| Prepare and record a 1:1 | `/sdr-manager:one-on-one` | `sdr-one-on-one` |

In other tools, you can always just ask in plain words. VS Code also lists them as slash commands, such as `/sdr-scorecard`.

### Setup

**What it does:** checks your computer, creates a folder for your team's data, and saves your team profile.

**When to use it:** once at the start, then whenever a rep joins or leaves, or a target changes.

```text
/sdr-manager:setup          Set up a real team, or update an existing one
/sdr-manager:setup sample   Try the plugin with the made-up team
```

**What it asks you:**

1. Your company and product, in a sentence or two
2. Who your ideal customer is
3. Each rep's name and start date, and any other spelling of their name in your tools
4. Which channels your team uses: calls, email, LinkedIn
5. Anyone in your exports who isn't a rep, such as you
6. Whether to keep each starting target or replace it

**Example:**

```text
You:     /sdr-manager:setup
Claude:  Your computer is ready. Where should I keep your team's data?
         The default is a folder called sdr-workspace, right here.
You:     That's fine.
Claude:  What does your company sell, and who's your ideal customer?
You:     Scheduling software for dental clinics with 5 to 50 staff.
Claude:  Who's on your team? I need each rep's name and start date.
You:     Maria Lopez, March 2025. Tom Becker, started two weeks ago.
Claude:  Thanks. Here are your starting targets and where each comes from...
```

**What you get:** a team profile saved in your workspace. Your data stays there, separate from the plugin, so updates can't erase it.

### Scorecard

**What it does:** reads your exports, calculates every metric, finds each rep's coaching focus, and builds a PDF.

**When to use it:** once a week.

```text
/sdr-manager:scorecard                          Use the exports in your workspace
/sdr-manager:scorecard ~/Downloads/week-44      Use a folder of exports
/sdr-manager:scorecard 2026-W44                 Report on a particular week
```

**What happens:**

1. It looks at each file's column names and a masked preview.
2. On the first run, it explains what it thinks each column means and asks you to confirm.
3. It asks about holidays and time off.
4. It calculates everything and checks the data for problems.
5. It writes short coaching notes, then builds the PDF.
6. It summarizes the results in chat.

**Example:**

```text
You:     /sdr-manager:scorecard ~/Downloads/week-44
Claude:  I found four exports. In the call file, I'm counting "Connected"
         as a live conversation. "Voicemail", "No Answer", and "Busy" count
         as dials without a connection. Does that match how your team works?
You:     Yes.
Claude:  Were there any holidays or time off this week?
You:     Tom was out on Friday.
Claude:  Team status: 1 on track, 5 need attention, 1 onboarding.

         Ben Carter: Activity: 960 touches in four weeks against a target
         of 2,080.
         Chloe Nguyen: Response: Email reply rate is 1.3% against a target
         of 3.43%.
         ...
         Your report is ready: sdr-workspace/reports/2026-W44/team-report.pdf
```

Next time, it remembers your columns and skips the questions.

**If something's wrong,** it stops and asks rather than guessing:

| Situation | What happens |
|---|---|
| A name it doesn't recognize | Asks whether it's a new rep, another spelling, or someone to ignore |
| A new value, such as a new call outcome | Asks what it means |
| Two files cover the same channel | Asks which to use, so nothing is counted twice |
| Many unreadable rows | Shows examples, with personal details hidden, and asks how to proceed |
| No meetings file | Still builds the report, and says which steps need one |

### One-on-one

**What it does:** prepares a one-page sheet for a 1:1, then records what was agreed.

**When to use it:** before and after each 1:1.

```text
/sdr-manager:one-on-one Chloe Nguyen         Prepare for the meeting
/sdr-manager:one-on-one Chloe Nguyen --log   Record what was agreed
```

**Before the meeting:**

```text
You:     /sdr-manager:one-on-one Chloe Nguyen
Claude:  Do you have any call notes or observations to include?
You:     No.
Claude:  Chloe's prep sheet is ready. Activity is on target, and the focus
         is email replies, starting with list quality.
         Come back with --log after the meeting to record what was agreed.
```

**After the meeting:**

```text
You:     /sdr-manager:one-on-one Chloe Nguyen --log
         We agreed Chloe will clean the list and verify 50 addresses
         before each send. Check back on November 13.
Claude:  Here's the entry. Shall I save it?

           Focus: Response (email reply rate)
           Agreed: Clean the list and verify 50 addresses before each send
           Check by: 2026-11-13

You:     Yes.
Claude:  Saved. It'll appear on Chloe's next prep sheet.
```

## What the reports look like

These are simplified. Real reports are formatted PDFs. The numbers come from the sample team.

### Team report: first page

```text
 Andy Gheewalla                                         SDR TEAM REPORT
 ══════════════════════════════════════════════════════════════════════
 2026-W44 | OCT 26 TO NOV 1, 2026
 One rep is on track while the team has gaps across the funnel.

   • Each rep's gap sits at a different step, so coach them one by one.
   • Email deliverability is a concern for one rep.

   1 On track     5 Needs attention     1 Onboarding

 Team numbers, last four weeks
 ──────────────────────────────────────────────────────────────────────
 Metric                        Actual      Target    Status
 Touches                       12,600      12,480    ● On target
 Connect rate                    6.0%        5.4%    ● On target
 Email reply rate                4.0%       3.43%    ● On target
 Meeting rate                   10.8%      12.09%    ◐ Near
 Meetings held                     49        55.4    ◐ Near
 Show rate                      76.6%         80%    ◐ Near
 Acceptance rate                60.9%         60%    ● On target

 Reps
 ──────────────────────────────────────────────────────────────────────
 Ava Reyes      On track          Stretch: Connect rate is 7.0%.  13/9.2
 Ben Carter     Needs attention   Activity: 960 touches in four    4/9.2
                                  weeks against a target of 2,080.
 Chloe Nguyen   Needs attention   Response: Email reply rate is    6/9.2
                                  1.3% against a target of 3.43%.
 Nina Patel     Onboarding        Numbers shown without judgment.   1/none
 ──────────────────────────────────────────────────────────────────────
 Andy Gheewalla | Team report | 2026-W44
```

### Team report: one page per rep

```text
 2026-W44 | MONTH 20 IN ROLE | 5 WORKING DAYS, 20 IN FOUR WEEKS
 Chloe Nguyen                                        Needs attention
 ══════════════════════════════════════════════════════════════════════
 ┌ Coaching focus ───────────────┐   The five steps
 │ Response: Email reply rate is │   1 Activity            ● On target
 │ 1.3% against a target of      │     Touches: 2,280 against 2,080
 │ 3.43%.                        │   2 Response            ○ Below
 │                               │     Email reply rate: 1.3% against 3.43%
 │ Check list quality before     │   3 Meetings booked     ● On target
 │ working on the writing.       │   4 Meetings held       ● On target
 │                               │   5 Meetings accepted   ● On target
 │ Deliverability warning:       │   = Outcome             ○ Below
 │ bounce rate is 3.0%.          │     Meetings held: 6 against 9.2
 └───────────────────────────────┘

 Numbers                     This week    Last four weeks    Target
 ──────────────────────────────────────────────────────────────────────
 Touches                           570              2,280     2,080
 Connect rate                     2.9%               2.9%      5.4%
 Email reply rate                 1.3%               1.3%     3.43%
 Meetings held                       2                  6       9.2

 Weekly trend
 Touches      Connect rate     Email reply     Meetings held
 ───────      ────────────     ───────────     ──╲__╱──
 570          2.9%             1.3%            2
```

The last page lists the data used and every target with its source.

### 1:1 prep sheet

```text
 Andy Gheewalla                                               1:1 PREP
 ══════════════════════════════════════════════════════════════════════
 Chloe Nguyen                                        Needs attention
 ══════════════════════════════════════════════════════════════════════
 ┌ Coaching focus ───────────────┐   Wins
 │ Response: Email reply rate is │   • Touches: 2,280 against 2,080
 │ 1.3% against a target of      │   • Meeting rate: 12.5% against 12.09%
 │ 3.43%.                        │   • Show rate: 85.7% against 80%
 │                               │   • Acceptance rate: 66.7% against 60%
 │ EVIDENCE                      │
 │ • Email reply rate by week:   │
 │   1.3%, 1.3%, 1.3%, 1.3%      │
 │ • Meetings held: 6 against 9.2│
 └───────────────────────────────┘

 Commitments from last time          Questions to ask
 ───────────────────────────────     ──────────────────────────────────
 • Clean the prospect list and       1. Where did these bad addresses
   verify 50 addresses before          come from?
   each send                         2. Which emails got replies, and
                                       what did they have in common?

 Agenda                              Meeting notes
 ───────────────────────────────     ──────────────────────────────────
  5 min   Check-in                   ..................................
 10 min   Wins and commitments       ..................................
 10 min   Coaching focus             ..................................
  5 min   Next steps                 ..................................
 ──────────────────────────────────────────────────────────────────────
 Andy Gheewalla | 1:1 prep | Chloe Nguyen | 2026-W44
```

## How the coaching focus works

The scorecard follows each rep through the same five steps over the last four weeks. The first step behind target becomes their one coaching focus, because fixing an early step often lifts everything after it.

```text
  1 Activity        Are they reaching enough people?
       │            Touches against target
       ▼
  2 Response        Are people responding?
       │            Connect, email reply, and LinkedIn rates
       ▼
  3 Meetings booked Are conversations becoming meetings?
       │            Meeting rate
       ▼
  4 Meetings held   Are prospects showing up?
       │            Show rate
       ▼
  5 Meetings accepted  Do AEs accept them?
                       Acceptance rate
```

| First weak step | Usual cause | What the 1:1 works on |
|---|---|---|
| Activity | Time or focus | Daily plan and protected calling time |
| Response | Poor prospect list or timing | Who they target and when they call |
| Meetings booked | Talk track or objection handling | Practice on the moment calls go wrong |
| Meetings held | Weak qualification or no confirmation | How they qualify and confirm |
| Meetings accepted | Wrong prospects | What a good prospect looks like |

These causes are starting points for a conversation, not verdicts.

### Rep statuses

| Status | Meaning |
|---|---|
| On track | Meeting goal met, and meetings are being accepted |
| Watch | A step is slightly behind, and none is far behind |
| Needs attention | At least one step is well behind |
| Review | Short of the goal, but no step explains why |
| Onboarding | In the first 30 days, so numbers aren't judged |
| Limited data | Not enough information, usually because a file is missing |

A step is **Near** from 85% to under 100% of target, and **Below** under 85%. Small samples show **Not enough data** instead of a judgment.

New hires have lower count targets: none in their first 30 days, then 50%, 75%, and full targets from month 4.

## What to export from your sales tools

Export from whatever you use, such as Salesforce, HubSpot, Outreach, Salesloft, or Apollo. Column names don't matter, because the plugin works out what each one means and checks with you.

| Export | What it needs to show | Example columns |
|---|---|---|
| Calls | Date, rep, call result | `Activity Date`, `Assigned To`, `Call Result` |
| Emails | Date, rep, replied, bounced | `Sent At`, `Owner`, `Replied`, `Bounced` |
| LinkedIn | Date, rep, action, result | `Date`, `Rep`, `Action`, `Result` |
| Meetings | Rep, date booked, meeting date, status, AE decision | `Owner Name`, `Date Booked`, `Meeting Status` |

Good to know:

- **First run:** export the last four full weeks plus the current week, so trends work from day one.
- **Meetings:** always cover at least the last six weeks, because statuses change after booking.
- **One file per channel:** if two tools log the same calls, choose one, or they'd be counted twice.
- **Weekly totals work too:** a file with one row per rep per week is fine.
- **Missing a channel?** The report still works. It leaves that channel out of the targets.

## Your weekly routine

```text
 Monday                                              During the week
 ┌───────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
 │ Export last week  │ ► │ Run the scorecard   │ ► │ Prep each 1:1       │
 │ from your tools   │   │ and read the PDF    │   │ then log what was   │
 └───────────────────┘   └─────────────────────┘   │ agreed              │
                                                   └─────────────────────┘
```

## Targets

Starting targets are published figures, and each one is listed with its source on the report's last page.

| Target | Starting value | Source |
|---|---|---|
| Dials, emails, and LinkedIn touches per day | 44, 41, and 19 | [The Bridge Group 2025](https://www.bridgegroupinc.com/research/2025-sdr-models-metrics-report-the-bridge-group), median |
| Connect rate | 5.4% | [Gong Labs 2024](https://www.gong.io/blog/the-hidden-power-of-cold-calling-insights-from-300m-calls), average |
| Email reply rate | 3.43% | [Instantly 2026](https://instantly.ai/cold-email-benchmark-report-2026), average |
| LinkedIn acceptance and reply rates | 28.5% and 10.4% | [Expandi 2026](https://expandi.io/blog/linkedin-outreach-benchmarks-2026/), average |
| Meeting rate | About 12.1% | Calculated so the funnel adds up to the meeting goal |
| Meetings held per month | 10 | The Bridge Group 2025, median quota |
| Show rate | 80% | [Operatix 2021](https://www.operatix.net/blogs/sdr-metrics-outbound-inbound-teams/) |
| Acceptance rate | 60% | Derived from The Bridge Group 2025 median quotas |
| Email bounce rate limit | Under 2% | Instantly 2026 |

**Replace these with your own numbers as soon as you can.** Most sources are vendors reporting their own data, and definitions vary. On target means typical, not excellent. The meeting rate is higher than published figures for calls alone, so that step may appear often until you set your own number.

## Privacy: how your data is handled

This plugin touches both employee performance and prospect details, so here's exactly what happens.

**What stays on your computer:**

- Your full export files. Scripts read them locally
- Everything in your team's workspace folder

**What your AI tool reads, and sends to its provider:**

- Column names and a masked preview of each export. Prospect names, emails, phone numbers, companies, and free-text notes are hidden
- Your team profile, including rep names and start dates
- The calculated metrics for each rep
- Coaching notes, when you prepare a 1:1
- Anything you paste into the chat, such as call notes

Anything your AI tool reads is handled under the terms of your plan with that tool. With Claude, that's your Claude plan.

**What's stored:**

- History holds counts and rep names. Prospect names, emails, phone numbers, and companies are not kept
- Exports you leave in the workspace's `imports` folder stay there until you delete them
- Coaching notes are plain text files on your computer

**Please keep your workspace folder private.** Don't put it in a shared drive. It's set up so Git ignores it.

### What it won't do

- Send messages, or change anything in your sales tools
- Rank reps against each other
- Recommend hiring, firing, pay, or formal performance action. If asked, it offers the facts and suggests involving HR
- Write statistics into a report. The calculator produces every number, and a check blocks any report where the written notes state one of their own. The one exception is a number from your own coaching notes, such as an agreed "50 dials"
- Guess anyone's gender from their name

## Customizing

| To change | Do this |
|---|---|
| Your targets | Run setup and say what to change |
| A rep's details | Run setup and say what changed |
| The report brand | Edit `name` in `assets/brand.json`. For a Claude Code install, fork this repository first, or your change will be lost on update |
| The report's look | Edit `assets/templates/report.css` |
| The coaching advice | Edit `references/coaching-playbook.md` |

## Troubleshooting

| Problem | Fix |
|---|---|
| "Python not found" | Install it from [python.org/downloads](https://www.python.org/downloads/). On Windows, tick **Add python.exe to PATH** |
| The skills don't appear | Restart your AI tool. For other tools, confirm that `~/.agents/skills/sdr-setup/SKILL.md` exists |
| You got a web page instead of a PDF | No browser was found. Open the file in any browser, print it, and choose **Save as PDF** |
| An Excel file won't open | Save it as CSV from Excel, or run `pip install openpyxl` |
| "There's no team workspace in this folder" | Open your AI tool in the folder that holds `sdr-workspace`, or run setup |
| A report says "Partial week" | Your exports stop before the end of the week. Export again once the week is over |
| Everything shows "Not enough data" | The sample is too small to judge fairly. Export more weeks |
| Every rep shows the same weak step | The report calls this a team pattern. Look at the list, messaging, or targets first |

## What's tested

| Area | Status |
|---|---|
| Plugin in Claude Code on macOS | Tested end to end with real sessions |
| Standalone skills, using `install.py` | Tested end to end in a real session |
| Python 3.9 and 3.12 | Over 450 automated tests pass, with 97% coverage of the program's code |
| PDF creation with Chrome | Tested |
| Gemini CLI | Confirmed it finds the skills. No full session has been run |
| Codex, Cursor, and VS Code Copilot | Their official docs confirm the skills folder. No full session has been run |
| Windows and Linux | **Not tested yet.** Steps are based on each tool's documentation |
| Edge, Chromium, and Brave for PDFs | **Not tested yet** |
| Cowork in the Claude desktop app | **Not tested yet** |
| Real company exports | **Not tested yet.** Tested with deliberately messy sample files |

If you try an untested setup, please [open an issue](https://github.com/mangollc/claude-SDR-Manager-plugin/issues) with what happened.

## For developers

```text
.claude-plugin/   Plugin and marketplace files
skills/           The three skills: setup, scorecard, one-on-one
references/       Coaching playbook, metric definitions, file mapping guide
scripts/          The calculator and report builder (standard library only)
assets/           Starting targets, brand, and report templates
sample-data/      The made-up team and messy exports
install.py        Installs the skills for tools other than Claude Code
tests/            The test suite
docs/             The design spec and build plan
```

Claude writes judgment, and scripts do the math. Every number on a report comes from `scripts/sdrlib/metrics.py`, and `scripts/sdrlib/narrative_check.py` rejects any written text that states its own.

```bash
python3 -m unittest discover -s tests -t .
```

The tests need nothing installed. To regenerate the sample data, run `python3 tests/make_sample_data.py`.

## Roadmap

- **Stage 2:** cadence audits, rewriting email, call, and LinkedIn steps, deliverability checks, and legal limits
- **Stage 3:** new-hire onboarding plans, cold call role-play, and call scoring
- **Stage 4:** team work rhythm, prospect journey, leadership slides, capacity planning, and live connections to sales tools

Not included yet: inbound leads, pipeline dollar values, and compensation.

## License

[MIT](LICENSE)
