# sdr-manager: First Build Design

- **Date:** 2026-10-30
- **Status:** Built. Section 10's statistics rule changed during final testing
- **Plugin name:** `sdr-manager`
- **First version:** 0.1.0

## 1. Summary

`sdr-manager` is a Claude plugin for anyone who manages a team of sales development reps (SDRs). SDRs make first contact with potential customers and book meetings for account executives (AEs).

The first build gives a manager one weekly loop:

1. Set up the team once.
2. Turn sales exports into a scorecard PDF each week.
3. Prepare for each rep's 1:1, then record what was agreed.

The core idea is that the scorecard follows every rep through the same five steps and finds the first step below target. That step becomes the rep's one coaching focus, so the manager gets a clear priority for each person instead of a wall of metrics.

## 2. Decisions already made

| Topic | Decision |
|---|---|
| Who it's for | Anyone who installs it. It assumes no company, product, or sales tool. |
| Who uses it | The manager, not the reps. |
| Data | CSV and Excel exports first. Live tool connections come later. |
| Lead types | Outbound only. |
| First workflow | Team profile, weekly scorecards, and 1:1 prep. |
| Report format | PDF. Slides arrive with leadership reports in stage 4. |
| Report branding | Every report carries the team's own name, which setup asks for. |
| Targets | Built-in starting targets, labeled with their source and editable by each team. |
| Calculations | A bundled Python calculator does all the math. |
| Limits on Claude | Claude analyzes and drafts. It never sends anything or changes anything in a sales tool. |

## 3. Scope

**In the first build:**

- `/sdr-manager:setup`, `/sdr-manager:scorecard`, and `/sdr-manager:one-on-one`
- Reading CSV and Excel exports from any sales tool
- Metrics for calls, email, and LinkedIn
- A team report PDF and a 1:1 prep PDF
- A saved coaching history for each rep
- A sample team so anyone can try the plugin before using real data

**Not in the first build:**

- Inbound leads
- Live connections to sales tools
- Sending messages or editing cadences
- Slides, Excel reports, or interactive dashboards
- Leaderboards or rankings
- Pipeline dollar value, compensation, or quota calculations
- Texts and other touches outside calls, email, and LinkedIn
- Combining several teams into one report (each team gets its own workspace)

## 4. Manager experience

### 4.1 `/sdr-manager:setup`

Run once, and again whenever the team changes.

1. Check for Python 3.9 or newer. If it's missing, give plain install steps for the manager's operating system and stop.
2. Offer two paths: try the sample team, or set up a real team.
3. For a real team, ask where to keep team data. The default is `sdr-workspace` in the current folder. If a workspace already exists, update it instead of replacing it.
4. Ask in small plain-language batches:
   - The company and product, in a sentence or two
   - The name to show on reports
   - The ideal customer
   - Each rep's name, start date, and any other spelling of their name used in exports
   - The outreach channels the team uses
   - Whether to keep each starting target or replace it
5. Save the team profile and show a short summary.

The sample path creates an `sdr-demo` workspace from the bundled sample data, so `/sdr-manager:scorecard` works immediately.

### 4.2 `/sdr-manager:scorecard`

Run weekly. It accepts an optional folder or file path and an optional week, such as `2026-W44`.

1. Find the workspace. If there isn't one, send the manager to setup.
2. Find the exports. On a first run, ask for the last four full weeks plus the current week, so trends work from day one.
3. Inspect each file (see section 6.2).
4. Reuse a saved mapping if the file's columns match one. Otherwise explain in plain language what each column appears to mean and ask the manager to confirm.
5. Ask about holidays and time off for the week. Save the answer so a re-run doesn't ask again.
6. Normalize the files. Stop and ask if there are unknown rep names, unknown values, or too many rejected rows (section 11).
7. Calculate metrics, statuses, and coaching focus.
8. Write short observations using the coaching playbook.
9. Confirm those observations state no statistics of their own.
10. Build the PDF and summarize it in chat: team status, who needs attention, the file location, and any data warnings.

### 4.3 `/sdr-manager:one-on-one`

Takes a rep's name. It has two modes.

**Before the meeting (default):**

1. Load the rep's latest metrics, trends, and coaching history. If the rep has no metrics, send the manager to the scorecard. If the latest metrics are more than 7 days old, warn but continue.
2. Offer to include call notes, transcripts, or the manager's own observations. These shape the questions and are not scored in this version.
3. Write the prep: praise for the rep, why the focus matters, progress on last time's commitments, questions to ask, and agenda topics. The calculator supplies the wins and evidence that carry numbers.
4. Confirm the text states no statistics of its own.
5. Build a one-page PDF.

**After the meeting (`--log`):**

1. Ask what was discussed and agreed.
2. Show the entry for confirmation.
3. Add it to the rep's coaching history.

The next prep starts from these commitments, and the numbers show whether they helped.

## 5. Architecture

Skills hold the judgment. Scripts hold the math. The workspace holds the team's data.

```text
Manager's exports
      │
      ▼
inspect ──► Claude and the manager confirm what the columns mean
      │
      ▼
normalize ──► daily counts per rep, with prospect details removed
      │
      ▼
metrics ──► numbers, statuses, and coaching focus (JSON)
      │
      ▼
Claude writes observations ──► check-narrative blocks any statistic
      │
      ▼
report ──► HTML ──► PDF through Chrome or Edge
```

### 5.1 Plugin layout

```text
sdr-plugin/
├── .claude-plugin/plugin.json
├── README.md
├── skills/
│   ├── setup/SKILL.md
│   ├── scorecard/SKILL.md
│   └── one-on-one/SKILL.md
├── references/
│   ├── file-mapping-guide.md      how to read common export formats
│   ├── metric-definitions.md      plain-language definitions
│   └── coaching-playbook.md       what to do at each funnel step
├── scripts/
│   ├── sdr.py                     command-line entry point
│   └── sdrlib/
│       ├── environment.py         check Python, openpyxl, and browser
│       ├── file_reader.py         read CSV and Excel, produce safe previews
│       ├── profile.py             load team profile, match rep names
│       ├── normalize.py           apply mappings, build daily counts
│       ├── history.py             read and write workspace history
│       ├── targets.py             load targets, calculate derived targets
│       ├── metrics.py             calculate windows and rates
│       ├── focus.py               choose status and coaching focus
│       ├── scorecard.py           assemble and save the metrics file
│       ├── coaching.py            read and add coaching history
│       ├── narrative_check.py     compare written numbers with metrics
│       ├── reports.py             fill report templates
│       ├── pdf.py                 find a browser and print to PDF
│       └── workspace.py           create workspaces, load the sample
├── assets/
│   ├── default-targets.json
│   └── templates/
│       ├── team-report.html
│       ├── one-on-one.html
│       └── report.css
├── sample-data/
├── tests/
└── docs/superpowers/specs/
```

Scripts use only the Python standard library at runtime, so there is nothing to install beyond Python. Excel files use `openpyxl` when it's already installed. If it isn't, the plugin asks the manager to save the file as CSV.

Skills reference bundled files with `${CLAUDE_PLUGIN_ROOT}`, never fixed paths. They try `python3`, then `python`, then `py -3`.

### 5.2 Workspace layout

The workspace lives outside the plugin, so updates can't erase it.

```text
sdr-workspace/
├── .gitignore                     ignores everything in this folder
├── team-profile.json
├── imports/2026-W44/              exports as supplied
├── mappings/                      saved column meanings
├── history/
│   ├── activity/2026-W44.csv      daily counts per rep
│   ├── meetings/2026-W44.csv      meeting snapshot from that week's export
│   ├── time-off/2026-W44.json
│   ├── sources/2026-W44.json      files used, rows read, rows rejected
│   └── metrics/2026-W44.json
├── reports/2026-W44/
│   ├── team-report.pdf
│   └── one-on-one-<rep>-2026-10-30.pdf
└── coaching/<rep>.md
```

An import replaces stored counts only for the channels and exact dates it contains, so a partial export or a stray old date can't wipe out good history, and re-runs always give the same result. A weekly summary counts as covering its whole week.

### 5.3 Team profile

`team-profile.json` holds:

- `company`, `product`, and `ideal_customer`, as short text
- `brand`: the name on the team's reports, in up to 60 characters
- `channels`: any of `call`, `email`, and `linkedin`
- `reps`: `name`, `start_date`, `aliases`, and `active`
- `ignored_names`: names in exports that aren't reps, such as the manager
- `targets`: each with `value`, `source`, and `as_of`. A value the team sets has `source: "team"`.

Managers never need to edit this file. They ask Claude or re-run setup.

## 6. Data contract

### 6.1 Accepted files

| Kind | Shape | Typical source |
|---|---|---|
| `activities` | One row per touch | CRM activity report, dialer log, sequence export |
| `rep_summary` | One row per rep per week | Tool summary reports |
| `meetings` | One row per meeting | CRM report |

Each channel must come from exactly one file, and so must meetings. If two files cover the same channel, such as a CRM and an outreach tool both logging calls, the plugin stops and asks which to use. This prevents double counting.

A `rep_summary` file must cover one week per row. A summary covering a longer period can't be split into weeks, so the plugin asks for a weekly version.

### 6.2 Inspection

`inspect` shows Claude the first 10 lines, the column names, the row count, and the distinct values of columns with 30 or fewer distinct values.

It masks two things:

- Columns whose names suggest prospect details or free text: email, phone, mobile, contact, prospect, lead, name, recipient, customer, company, account, organization, subject, notes, description, comments, body, message, title, URL, link, or profile. A name that also contains owner, rep, representative, SDR, user, assigned, or agent stays visible, because `Contact Owner` or `Account Owner` is usually the rep. So does a name describing an event rather than a person, such as `Email Status` or `Phone Disposition`, because Claude needs those values to map the file.
- Any value that looks like an email address or phone number.

Masked columns never appear in the distinct-value lists.

The full file is only read by the scripts.

### 6.3 Mapping

A mapping records what a file's columns mean. It contains:

- `signature`: a hash of the lowercased header row
- `kind`, `channel`, `header_row`, and `date_format`
- `columns`: which source column fills each standard field
- `flags`: which values count as connected, replied, bounced, or accepted
- `values`: how source values translate to standard values

Saved mappings are reused when the signature matches.

### 6.4 Standard fields

Activity rows become one row of counts per rep, date, and channel:

`date, rep, channel, granularity, dials, connected, emails, replies, bounces, li_requests, li_accepted, li_messages, li_replies, li_other`

`granularity` is `day` for `activities` files. `rep_summary` rows use `week` and are dated the Monday of that week, so days active isn't available for them.

Meeting rows become:

`rep, booked_date, due_date, status, accepted`

- `status` is one of `held`, `no_show`, `cancelled`, `rescheduled`, or `scheduled`.
- `accepted` is `yes`, `no`, or `pending`.
- If `due_date` is missing, the booked date is used and the report says so.

Prospect names, email addresses, phone numbers, and company names are not carried forward. Only counts and rep names reach the stored history.

The meetings export must cover at least the last six weeks, because statuses change after booking. The newest snapshot replaces earlier ones for all calculations.

## 7. Metrics

### 7.1 Time windows

- Weeks run Monday to Sunday and use ISO week names, such as `2026-W44`.
- Without a chosen week, the scorecard uses the latest week with data.
- Each scorecard shows **this week** and **the last four weeks**, including this week.
- Statuses and coaching focus use the four-week window, because one week has too few meetings to judge. A rep with less history uses what's available.
- Working days are Monday to Friday, minus team holidays and the rep's time off.
- Weekend touches count toward totals without adding working days.

### 7.2 Definitions

| Metric | Calculation |
|---|---|
| Touches | Dials + emails + LinkedIn requests, messages, and other touches |
| Connect rate | Connected calls ÷ dials |
| Email reply rate | Replies ÷ emails sent |
| Email bounce rate | Bounces ÷ emails sent |
| LinkedIn acceptance rate | Accepted requests ÷ requests sent |
| LinkedIn reply rate | Replies ÷ messages sent |
| Conversations | Connected calls + email replies + LinkedIn replies |
| Meeting rate | Meetings booked ÷ conversations |
| Meetings booked | Meetings with a booked date in the window |
| Meetings held | Held meetings with a due date in the window |
| Meetings due | Held + no-show + cancelled meetings with a due date in the window |
| Show rate | Held ÷ meetings due |
| Acceptance rate | Accepted ÷ held meetings reviewed (`yes` or `no`) |
| Days active | Working days with at least one touch |

Rescheduled and future meetings are left out of show rate. Pending meetings are left out of acceptance rate and shown as a separate count.

## 8. Starting targets

These ship in `assets/default-targets.json`. Each team can replace any of them.

| Target | Starting value | Stretch | Source |
|---|---|---|---|
| Dials per working day | 44 | None | Bridge Group 2025, median |
| Emails per working day | 41 | None | Bridge Group 2025, median |
| LinkedIn touches per working day | 19 | None | Bridge Group 2025, median |
| Connect rate | 5.4% | 13.3% | Gong Labs 2024, average and top quartile |
| Email reply rate | 3.43% | 5.5% | Instantly 2026, average and top 25% |
| LinkedIn acceptance rate | 28.5% | None | Expandi 2026, platform average |
| LinkedIn reply rate | 10.4% | None | Expandi 2026, platform average |
| Meeting rate | Derived, about 12.1% | None | Calculated from the other targets |
| Meetings held per month | 10 | None | Bridge Group 2025, median quota |
| Show rate | 80% | None | Operatix 2021, a 20% dropout rate |
| Acceptance rate | 60% | None | Derived from Bridge Group 2025 median quotas (6 converted ÷ 10 held) |
| Email bounce rate limit | Under 2% | None | Instantly 2026 |

**How to read these:**

- Response-rate targets are published averages, so "on target" means typical, not excellent.
- Activity targets describe normal workload. They aren't a recommendation to push volume higher.
- Most sources are vendors reporting their own data, and definitions vary between them.
- The Operatix figure is the oldest. Teams should replace it first.
- Only 60% of SDRs reached quota in the Bridge Group study, so a normal team will have some reps below the meeting target.
- Belkins' 2025 data is a useful second reference for calls: 9.9% connect rate and 4.6% of conversations booked, across 175,000+ dials.

### 8.1 Derived meeting rate

The published meeting rates cover calls only, so they don't fit a blended rate across three channels. The target is calculated so the funnel adds up to the meeting goal:

```text
booked per week = (meetings held per month ÷ show rate) ÷ (52 ÷ 12)

conversations per week = 5 × (
    dials per day × connect rate
  + emails per day × email reply rate
  + LinkedIn touches per day × 0.5 × LinkedIn reply rate
)

meeting rate target = booked per week ÷ conversations per week
```

Only channels the team uses are included. The 0.5 assumes half of LinkedIn touches are messages.

With the defaults, this gives 2.88 ÷ 23.85 = 12.1%. The value updates when a team changes its targets, unless the team sets its own meeting rate.

This is well above the 4.6% that Gong and Belkins report for calls alone, because it has to carry the whole meeting goal. Expect step 3 to appear often until a team sets its own numbers.

### 8.2 New-hire ramp

Count targets (touches and meetings) scale with time in role. Rate targets don't change.

| Month in role | Multiplier |
|---|---|
| 1 | 0%, numbers shown without judgment |
| 2 | 50% |
| 3 | 75% |
| 4 onward | 100% |

Month 1 is the first 30 days from the start date, and each later month is the next 30 days. This matches the three-month average ramp in Bridge Group 2025 and the phased plan published by SalesHive.

For each week in the window, the count target is the daily target × working days × that week's multiplier. A week's multiplier uses the rep's month in role on that week's Sunday. Actual counts include every week in the window.

Meetings held per month convert to a daily target by dividing by 21.67 working days (52 ÷ 12 × 5). A full four-week window at the default target is 9.2 meetings held.

### 8.3 Status rules

| Status | Actual compared with target |
|---|---|
| On target | 100% or more |
| Near | 85% to under 100% |
| Below | Under 85% |
| Not enough data | Sample is under the minimum |
| Not available | The data wasn't supplied |

A count target of zero gives Not available, so a rep with no working days in the window can't pass by default.

Minimum samples over the four-week window are plugin defaults, not published figures:

| Metric | Minimum |
|---|---|
| Connect rate | 100 dials |
| Email reply rate | 100 emails |
| LinkedIn acceptance rate | 30 requests |
| LinkedIn reply rate | 30 messages |
| Meeting rate | 20 conversations |
| Show rate | 5 meetings due |
| Acceptance rate | 5 meetings reviewed |

## 9. Coaching focus

### 9.1 The five steps

| Step | Measure | Status rule |
|---|---|---|
| 1. Activity | Touches, summed across channels with data | Compare the total with the matching target total |
| 2. Response | Connect, email reply, LinkedIn acceptance, and LinkedIn reply rates | The worst metric with enough data sets the step's status |
| 3. Meetings booked | Meeting rate | Compare with target |
| 4. Meetings held | Show rate | Compare with target |
| 5. Meetings accepted | Acceptance rate | Compare with target |

The **outcome** is meetings held in the window compared with the count target.

When step 2 is the focus, the focus names its weakest metric.

Email bounce rate isn't a step. At 2% or higher, with at least 100 emails, the report shows a deliverability warning, since a high bounce rate can drag down reply rates.

### 9.2 Choosing the status and focus

Apply these rules in order. The first match wins.

1. **Onboarding:** the rep is in month 1 on the Sunday of the selected week. Show numbers with no focus.
2. **On track:** meetings held meet the target, and step 5 isn't Below. The focus is the metric with the lowest actual ÷ stretch among metrics that have a stretch value, enough data, and room to improve. If none qualifies, there's no focus.
3. **Needs attention:** at least one step is Below. The focus is the first Below step.
4. **Watch:** at least one step is Near. The focus is the first Near step.
5. **Review:** meetings held are under target but no step explains why. The report says to check for timing, such as meetings booked but not yet held.
6. **Limited data:** none of the above applies, usually because a file is missing. The report lists what's needed.

Steps marked Not enough data or Not available are skipped, and the report says so. Without a meetings file, steps 3 to 5 and the outcome are Not available, so rule 2 can't apply and the rep's status comes from steps 1 and 2 only.

### 9.3 Team pattern

Judged reps are all reps except those marked Onboarding or Limited data. If at least half of them share a focus step, and at least three reps share it, the team report says so. A shared problem usually points to the list, the messaging, or the targets rather than to each rep.

### 9.4 Coaching playbook

`references/coaching-playbook.md` gives each step its likely causes, checks, and practice ideas. Claude treats the causes as questions for the 1:1, never as conclusions.

| First weak step | Usual cause | What the 1:1 works on |
|---|---|---|
| Activity | Time or focus | Daily plan and protected calling time |
| Response | Poor prospect list or timing | Who they target and when they call |
| Meetings booked | Talk track or objection handling | Practice on the moment calls go wrong |
| Meetings held | Weak qualification or no confirmation | How they qualify and confirm |
| Meetings accepted | Wrong prospects | What a good prospect looks like |

## 10. Reports

Both reports use US Letter and system fonts, so they work offline. Status always appears as text as well as color, so reports still work in grayscale.

**Branding:** every report shows the team's name as a wordmark at the top of its first page, in the footer of every page, and in the PDF's document title. Setup asks for the name and saves it as `brand` in `team-profile.json`. A team without one shows its company, then `SDR Manager`. Only the name can be set, so the report keeps its own logo-free palette.

**Team report:**

- Page 1: week and date range, team totals against targets, the number of reps in each status, any team pattern, up to three observations, and an overview of every rep.
- One page per active rep: status, coaching focus, this week and four-week numbers against targets, step-by-step status, data notes, and a small weekly trend for touches, connect rate, email reply rate, meetings booked, and meetings held.
- Reps appear alphabetically. There are no rankings.
- A final page lists the data used, then every target with its source and date.

**1:1 prep:**

- One page with the rep's status, wins, coaching focus with evidence, last commitments with progress, questions to ask, and agenda topics.

**PDF creation:** the plugin finds Chrome, Edge, Chromium, or Brave and prints the report with a 60-second time limit. If that fails, it keeps the HTML file and tells the manager to open it and choose Save as PDF.

**Statistics rule:** Claude's written text states no statistics. It carries judgment only, and every number on a page comes from the calculator. Before rendering, `check-narrative` rejects any number in that text, in digits or in words. Dates, step numbers, the term 1:1, the word "one", and the fixed "four-week" period are allowed. So are numbers from the rep's own coaching history, such as an agreed "50 dials". Questions and agenda topics may use number words, because they're suggestions rather than claims, but no digits. The same check rejects gendered pronouns, because a name says nothing certain about anyone's gender. Fixed agenda timings live in the template.

This replaced an earlier rule that only checked each number existed somewhere in the metrics file. A real test session showed why that wasn't enough: it wrote "960 this week" for a four-week total, and "Thirteen held this week but only three accepted", mixing periods. Both passed. A number can be real and still be attached to the wrong rep or period, so numbers now only appear where the calculator puts them.

## 11. Error handling

| Situation | Behavior |
|---|---|
| Python missing or too old | Setup gives install steps and stops |
| No workspace | Send the manager to setup |
| Unknown rep name | Stop. Add an alias, add the rep, or ignore the name |
| Unmapped value in a mapped column | Stop and ask, so a new call outcome is never silently counted as a miss |
| Row with no valid date, or no rep | Reject the row and count it |
| More than 5% of a file rejected | Stop and show examples, with personal details masked |
| Two files cover one channel | Stop and ask which file to use |
| Channel missing | Show Not available and leave it out of targets |
| No meetings file | Build the report, mark steps 3 to 5 Not available, and explain what's missing |
| Division by zero | Show Not available, never zero |
| Latest activity date in the selected week is before Friday | Show a partial-week banner and count working days only through that date |
| Rep has no working days in a week | Show Out for that week |
| Rep has no start date | Treat them as fully ramped and add a note |
| Acceptance still pending | Leave it out of the rate and show the pending count |
| Excel file without `openpyxl` | Ask the manager to save it as CSV |
| Number check fails | Rewrite the text and check again |
| No browser found, or PDF fails | Keep the HTML file and give Save as PDF steps |

Every report lists the files used, rows read, rows rejected, and date range.

## 12. Privacy and people safety

- The plugin has no server and sends nothing anywhere itself. Anything Claude reads is handled under the terms of the manager's Claude plan, and the README says this plainly.
- Claude sees column names and masked samples, not full exports.
- Stored history holds counts and rep names, not prospect details.
- The workspace `.gitignore` keeps coaching notes and exports out of Git.
- Setup warns that coaching notes are sensitive and shouldn't sit in a shared folder.
- Reports describe coaching needs only. Claude doesn't recommend hiring, firing, pay, or formal performance action. If asked, it offers the facts and suggests involving HR.
- Reports don't rank reps against each other.

## 13. Testing

Development follows test-first practice, with at least 80% coverage of the scripts.

**Calculator tests:**

- A small fixture with hand-worked answers for every metric, status, and derived target
- Each rule in section 9.2
- Ramp multipliers, time off, partial weeks, and pending acceptance

**Messy file tests:**

- Renamed columns, a header row that isn't the first line, footer rows, semicolon-separated files, and non-UTF-8 text
- Missing channels, unknown reps, unknown values, and two files for one channel

**Sample team:**

The design review described six reps. The final sample has seven, because a new hire is needed to exercise onboarding:

| Sample rep | Expected result |
|---|---|
| Healthy performer | On track, with a stretch focus |
| Low activity | Step 1 |
| Good activity, weak response | Step 2 |
| Good response, few meetings | Step 3 |
| Many meetings, many no-shows | Step 4 |
| Many held meetings, low acceptance | Step 5 |
| New hire | Onboarding |

The sample exports are deliberately messy and use tool-neutral column names, so the demo exercises the mapping step. All names and data are made up.

**End-to-end checks:**

- `claude plugin validate` passes.
- The plugin installs from this folder into Claude Code.
- All three commands run against the sample team.
- Both PDFs are checked by eye.
- Each sample rep gets the expected result.

## 14. Success criteria

1. A new user can install the plugin and get a sample team report in under 10 minutes.
2. All seven sample reps get their expected status and focus.
3. Calculator results match every hand-worked answer exactly.
4. A messy export maps correctly after one round of manager confirmation.
5. Every number in a report comes from the calculator or the coaching history, and Claude's written text states no statistics of its own.
6. A saved commitment from one 1:1 appears in the next prep with its progress.

## 15. Risks

| Risk | Response |
|---|---|
| Non-technical managers may not have Python | Setup checks first and gives plain steps |
| The plugin is first tested on macOS in Claude Code | README states what was tested. Windows, Linux, and Cowork need testing before they're claimed as supported |
| A Cowork environment may lack Python or a browser | The HTML fallback covers the browser. Python needs a check during release |
| Published benchmarks may not fit a team | Targets are labeled, sourced, dated, and replaceable |
| A wrong column mapping skews results | Claude explains each mapping, and the manager confirms it |
| Numbers could be misused against reps | Coaching language, no rankings, and no employment recommendations |

## 16. Later stages

- **Stage 2:** cadence audits, rewriting email, call, and LinkedIn steps, deliverability checks, and legal limits (CAN-SPAM, GDPR, TCPA, call-recording consent, LinkedIn automation rules).
- **Stage 3:** new-hire onboarding plans, cold call role-play, and call scoring.
- **Stage 4:** team work rhythm, prospect journey, full activity timeline, leadership slides, capacity planning, and live tool connections.

The first build stores daily activity counts, so the later activity timeline can start from existing history.

**Release:** published publicly at `mangollc/claude-SDR-Manager-plugin` under the MIT license, with a plugin marketplace for Claude Code and `install.py` for tools that read `~/.agents/skills`, such as Codex, Cursor, VS Code Copilot, and Gemini CLI.

## 17. Sources

Checked on 2026-10-30.

- [The Bridge Group, SDR Models, Motions & Metrics 2025](https://www.bridgegroupinc.com/research/2025-sdr-models-metrics-report-the-bridge-group): 350+ B2B companies. Daily activity, median quotas, ramp time, and share of SDRs at quota.
- [Gong Labs, Insights from 300M calls](https://www.gong.io/blog/the-hidden-power-of-cold-calling-insights-from-300m-calls), July 2024: connect rate and conversation-to-meeting rate.
- [Belkins, B2B Cold Calling Benchmarks 2026](https://belkins.io/blog/cold-calling-benchmarks): 175,000+ dials logged in 2025.
- [Instantly, Cold Email Benchmark Report 2026](https://instantly.ai/cold-email-benchmark-report-2026): platform data from January 1 to December 18, 2025. Reply rate tiers and bounce limit.
- [Expandi, LinkedIn Outreach Benchmarks 2026](https://expandi.io/blog/linkedin-outreach-benchmarks-2026/): 13.2 million requests from May 2025 to April 2026.
- [Operatix, SDR Metrics](https://www.operatix.net/blogs/sdr-metrics-outbound-inbound-teams/): published 2021, updated 2023. Meetings per month and dropout rate.
- [SalesHive, SDR Best Practices](https://saleshive.com/blog/sales-development-reps-best-practices-teams): phased ramp plan.
