# SDR Manager

**Your weekly coaching assistant for SDR teams.**

Download your team's activity from your sales tools, hand it to Claude, and get:

- A scorecard for every rep
- The one thing to coach each rep on
- A one-page prep sheet for every 1:1

You don't need to be technical. There's no code to write, and you talk to it in normal English.

```text
   Files from your            SDR Manager                What you get
   sales tools
 ┌────────────────┐      ┌────────────────────┐      ┌────────────────────┐
 │ Calls          │      │ Reads your files   │      │ Team report (PDF)  │
 │ Emails         │ ───► │ Does the math      │ ───► │ One page per rep   │
 │ LinkedIn       │      │ Finds each rep's   │      │ What to coach      │
 │ Meetings       │      │ biggest gap        │      │ 1:1 prep sheets    │
 └────────────────┘      └────────────────────┘      └────────────────────┘
```

## Contents

- [What it does for you](#what-it-does-for-you)
- [What you need](#what-you-need)
- [Install in 5 minutes](#install-in-5-minutes)
- [Try it with the sample team](#try-it-with-the-sample-team)
- [Use it with your real team](#use-it-with-your-real-team)
- [What you can ask for](#what-you-can-ask-for)
- [What the reports look like](#what-the-reports-look-like)
- [How it decides what to coach](#how-it-decides-what-to-coach)
- [What to download from your sales tools](#what-to-download-from-your-sales-tools)
- [Your weekly routine](#your-weekly-routine)
- [Where the targets come from](#where-the-targets-come-from)
- [Costs, accounts, and API keys](#costs-accounts-and-api-keys)
- [Privacy](#privacy)
- [Common questions](#common-questions)
- [What's been tested](#whats-been-tested)
- [Technical details](#technical-details)
- [What's coming next](#whats-coming-next)
- [License](#license)

## What it does for you

| Without SDR Manager | With SDR Manager |
|---|---|
| Hours in spreadsheets every week | A finished report in minutes |
| Guessing why a rep's numbers are down | One clear thing to coach each rep on |
| 1:1s that start from scratch | A prep sheet with what was agreed last time |
| Numbers scattered across different tools | One report, from any sales tool |

It covers cold calls, email, and LinkedIn. It works with any sales tool that lets you download your data, such as Salesforce, HubSpot, Outreach, Salesloft, or Apollo.

## What you need

| You need | Details |
|---|---|
| A computer | Mac or Windows |
| The Claude desktop app | Free to download |
| A paid Claude plan | Any paid plan works. The Code tab isn't available on the free plan |
| Python | A free program that does the math. You may already have it, and Claude will tell you if you don't |
| Chrome or Edge | Used to create PDFs. You probably already have one of these |

## Install in 5 minutes

You only need to do this once, and Claude does the installing for you.

### Step 1: Get the Claude app

If you don't have it yet, download it from [claude.ai/download](https://claude.ai/download), install it, and sign in.

### Step 2: Open the Code tab

1. In the Claude app, click the **Code** tab at the top of the sidebar. Don't let the name put you off, because you won't write any code. This is the part of Claude that can work with files on your computer.
2. Just under the message box, click the first button and choose the top option under **Local**. This keeps the work on your own computer.
3. Click the button next to it and choose **Open folder…**. Create a new folder called **SDR Reports**, and open it. SDR Manager keeps everything in this folder.

### Step 3: Ask Claude to install it

Paste this message and press Enter:

```text
Please install SDR Manager on this computer so I can use it in all my
projects. Download https://github.com/mangollc/claude-SDR-Manager-plugin
and follow the "Instructions for AI assistants" section of
docs/technical-guide.md.
```

Claude downloads SDR Manager and sets it up, which takes about a minute. It will ask for permission a few times, so allow each one. It tells you when it's finished.

If your company manages your computer or your Claude account and this doesn't work, send your IT team the [technical guide](docs/technical-guide.md).

### Using a different AI tool?

Paste the same message into Cursor, Codex, VS Code with Copilot, or Gemini CLI. Approve anything it asks to do, then close your AI tool and open it again.

## Try it with the sample team

Before using real data, try it with a made-up team of seven reps. All the names, companies, and numbers are fake. It takes about two minutes.

Stay in the **Code** tab, with your **SDR Reports** folder open.

1. Type this and press Enter:

   ```text
   Set up SDR Manager with the sample team.
   ```

2. Claude will ask for permission before it runs something or saves a file. Allow it each time. This is SDR Manager's calculator, running on your own computer. A first scorecard can take 15 to 20 of these, and later ones fewer, because it remembers your files.
3. Now type:

   ```text
   Run my SDR scorecard.
   ```

4. Claude shows you how it's reading each file. Say **yes** if it looks right, or just tell it what's wrong.
5. Claude asks which week you want and whether anyone had time off. For the sample team, say the latest week, with no time off.
6. Claude tells you where your PDF report is. Open it and have a look.
7. Finally, try a 1:1 prep sheet:

   ```text
   Prepare my 1:1 with Chloe Nguyen.
   ```

The sample team shows each situation the plugin looks for:

| Sample rep | What's going on | What SDR Manager says |
|---|---|---|
| Ava Reyes | Doing well | On track, with a stretch goal |
| Ben Carter | Not enough outreach | Coach on activity |
| Chloe Nguyen | Busy, but few replies | Coach on responses, and check the email list |
| Diego Marin | Good replies, few meetings | Coach on booking meetings |
| Priya Shah | Many no-shows | Coach on getting meetings to happen |
| Sam Okafor | AEs reject the meetings | Coach on who gets booked |
| Nina Patel | New hire | Onboarding, so no judgment yet |

## Use it with your real team

1. Open the **Code** tab, and open a new folder for your team, such as **My SDR Team**.
2. Type:

   ```text
   Set up SDR Manager for my team.
   ```

3. Answer a few questions about your product, your customers, and your reps.
4. Download your files. See [what to download](#what-to-download-from-your-sales-tools).
5. Type this, using wherever you saved your files:

   ```text
   Run my SDR scorecard. My files are in my Downloads folder.
   ```

The first time, Claude checks that it understands your files. After that, it remembers.

## What you can ask for

There are three things SDR Manager does. Just ask in your own words, or use the shortcut if you prefer.

| What you want | What to type | Shortcut |
|---|---|---|
| Set up or change your team | "Set up SDR Manager for my team" | `/sdr-setup` |
| Get the weekly report | "Run my SDR scorecard" | `/sdr-scorecard` |
| Prepare for a 1:1 | "Prepare my 1:1 with Chloe" | `/sdr-one-on-one Chloe` |
| Record what you agreed | "Log my 1:1 with Chloe" | `/sdr-one-on-one Chloe --log` |

Not every AI tool has shortcuts, but plain English works everywhere.

### Set up your team

**What it does:** saves the details Claude needs to give you useful advice.

**When to use it:** once at the start, then whenever a rep joins or leaves, or you want to change a target.

**What Claude asks:**

1. What your company sells
2. Who your ideal customer is
3. Your reps' names and start dates, and any other spelling of their names in your tools
4. Which channels your team uses: calls, email, LinkedIn
5. Anyone in your files who isn't a rep, such as you
6. Whether to keep the starting targets or use your own

**Example:**

```text
You:     Set up SDR Manager for my team.
Claude:  Your computer is ready. Where should I keep your team's data?
         The default is a folder called sdr-workspace, right here.
You:     That's fine.
Claude:  What does your company sell, and who's your ideal customer?
You:     Scheduling software for dental clinics with 5 to 50 staff.
Claude:  Who's on your team? I need each rep's name and start date.
You:     Maria Lopez, March 2025. Tom Becker, started two weeks ago.
Claude:  Thanks. Here are your starting targets and where each comes from...
```

### Get the weekly scorecard

**What it does:** turns your files into a PDF report, and picks one thing to coach for each rep.

**When to use it:** once a week.

**Example:**

```text
You:     Run my SDR scorecard. My files are in my Downloads folder.
Claude:  I found four files. In the call file, I'm counting "Connected" as a
         real conversation. "Voicemail" and "No Answer" count as attempts.
         Does that match how your team works?
You:     Yes.
Claude:  Were there any holidays or time off this week?
You:     Tom was out on Friday.
Claude:  Team status: 1 on track, 5 need attention, 1 onboarding.

         Ben Carter: Activity: 960 touches in four weeks against a target
         of 2,080.
         Chloe Nguyen: Response: Email reply rate is 1.3% against a target
         of 3.43%.
         ...
         Your report is ready.
```

**If something looks wrong,** Claude stops and asks rather than guessing. For example, it asks if it finds a name it doesn't know, or if two files seem to count the same calls.

### Prepare for a 1:1

**What it does:** builds a one-page sheet with wins, the coaching focus, questions to ask, and an agenda.

**When to use it:** before each 1:1.

**Example:**

```text
You:     Prepare my 1:1 with Chloe Nguyen.
Claude:  Do you have any call notes or observations to include?
You:     No.
Claude:  Chloe's prep sheet is ready. Activity is on target, and the focus
         is email replies, starting with list quality.
```

### Record what you agreed

**What it does:** saves what you and your rep agreed, so it appears on their next prep sheet.

**When to use it:** after each 1:1.

**Example:**

```text
You:     Log my 1:1 with Chloe. We agreed on cleaning the list and checking
         50 addresses before each send. Let's review on November 13.
Claude:  Here's the entry. Shall I save it?

           Focus: Response (email reply rate)
           Agreed: Clean the list and check 50 addresses before each send
           Check by: 2026-11-13

You:     Yes.
Claude:  Saved. It'll appear on Chloe's next prep sheet.
```

## What the reports look like

These are simplified versions. The real reports are formatted PDFs. All the numbers come from the sample team.

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
```

The last page of the report lists the files used and where every target comes from.

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
   check 50 addresses before           come from?
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

## How it decides what to coach

SDR Manager looks at the last four weeks and follows each rep through the same five steps. The first step that's behind target becomes their one coaching focus, because fixing an early problem often helps everything after it.

```text
  1 Activity            Are they reaching out to enough people?
       │
       ▼
  2 Response            Are people picking up and replying?
       │
       ▼
  3 Meetings booked     Are conversations turning into meetings?
       │
       ▼
  4 Meetings held       Are prospects showing up?
       │
       ▼
  5 Meetings accepted   Do your AEs accept those meetings?
```

| First step behind target | Usual cause | What to work on in the 1:1 |
|---|---|---|
| Activity | Time or focus | A daily plan and protected calling time |
| Response | A poor prospect list, or bad timing | Who they contact, and when |
| Meetings booked | Weak talk track or objection handling | Practice the moment calls go wrong |
| Meetings held | Weak qualifying, or no confirmation | How they qualify and confirm |
| Meetings accepted | Booking the wrong prospects | What a good prospect looks like |

These causes are places to start the conversation, not verdicts. The numbers show where a rep is behind, not why.

**What the statuses mean:**

| Status | Meaning |
|---|---|
| On track | Hitting the meeting goal, and AEs are accepting those meetings |
| Watch | A step is slightly behind |
| Needs attention | At least one step is well behind |
| Review | Short of the goal, but no step explains why |
| Onboarding | In their first 30 days, so the numbers aren't judged |
| Limited data | Not enough information, usually because a file is missing |

New hires get lower targets: none in their first 30 days, then 50%, then 75%, and full targets from month four.

## What to download from your sales tools

In most sales tools, open a report and look for **Export** or **Download**, then choose **CSV** or **Excel**. Don't worry about the column names. Claude works out what each one means, and checks with you.

| Download | It should show | Where to find it |
|---|---|---|
| Calls | Date, rep, and how each call went | Your dialer, CRM, or outreach tool |
| Emails | Date, rep, and whether it got a reply or bounced | Your outreach tool |
| LinkedIn | Date, rep, what was sent, and the result | Your LinkedIn or outreach tool |
| Meetings | Rep, date booked, meeting date, whether it happened, and whether the AE accepted it | Your CRM |

A few tips:

- **First time:** download the last four full weeks plus this week, so you get trends right away.
- **Meetings:** always include at least the last six weeks, because meetings change status after they're booked.
- **Use one file per channel:** if two tools both track the same calls, pick one. Otherwise, calls get counted twice.
- **Missing something?** That's fine. The report still works, and it tells you what's missing.
- **Can't get a daily list?** A weekly summary with one row per rep works too.

## Your weekly routine

```text
 Monday                                              During the week
 ┌───────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
 │ Download last     │ ► │ Ask for your        │ ► │ Prepare each 1:1,   │
 │ week's files      │   │ scorecard           │   │ then log what you   │
 └───────────────────┘   └─────────────────────┘   │ agreed              │
                                                   └─────────────────────┘
```

## Where the targets come from

To start with, SDR Manager uses published industry figures, so you don't need to know what good looks like. The last page of every report shows where each one comes from.

| Target | Starting value | Source |
|---|---|---|
| Daily dials, emails, and LinkedIn touches | 44, 41, and 19 | [The Bridge Group 2025](https://www.bridgegroupinc.com/research/2025-sdr-models-metrics-report-the-bridge-group) |
| Connect rate | 5.4% | [Gong Labs 2024](https://www.gong.io/blog/the-hidden-power-of-cold-calling-insights-from-300m-calls) |
| Email reply rate | 3.43% | [Instantly 2026](https://instantly.ai/cold-email-benchmark-report-2026) |
| LinkedIn acceptance and reply rates | 28.5% and 10.4% | [Expandi 2026](https://expandi.io/blog/linkedin-outreach-benchmarks-2026/) |
| Meeting rate | About 12.1% | Worked out from the other targets |
| Meetings held per month | 10 | The Bridge Group 2025 |
| Show rate | 80% | [Operatix 2021](https://www.operatix.net/blogs/sdr-metrics-outbound-inbound-teams/) |
| Acceptance rate | 60% | Worked out from The Bridge Group 2025 |
| Email bounce rate limit | Under 2% | Instantly 2026 |

**Use your own numbers as soon as you can.** Just ask: *"Change our connect rate target to 8%."* These are averages, so on target means typical, not excellent. Most come from companies reporting on their own customers, so treat them as a starting point.

## Costs, accounts, and API keys

**SDR Manager is free, and it needs no extra accounts or services.**

| Question | Answer |
|---|---|
| Does it cost anything? | No. You only need your paid Claude plan, or your other AI tool |
| Do I need API keys or passwords? | **No API keys, no passwords, and no special settings** |
| Does it connect to my CRM or sales tools? | No. You download the files yourself, and it never logs in to anything |
| Does it use any outside services? | **No.** SDR Manager itself never connects to the internet |
| What does it use on my computer? | Python for the math, and Chrome or Edge to make PDFs |

The one outside connection is your AI tool, because that's how you talk to it. See [Privacy](#privacy) for what your AI tool sees.

**For your IT team:** no API keys, no environment variables, and no external services. The [technical guide](docs/technical-guide.md) has the full details.

## Privacy

Your files include real people's information, so here's exactly what happens to it.

**What stays on your computer:**

- Your full downloaded files. A small program on your computer reads them
- Everything in your team's folder

**What your AI tool sees, and sends to the company behind it:**

- The column names in your files, plus a preview with prospect names, emails, phone numbers, companies, and notes hidden
- Your team details, including your reps' names and start dates
- Each rep's numbers
- Your coaching notes, when you prepare a 1:1
- Anything you type into the chat

This is covered by your agreement with your AI tool. For Claude, that's your Claude plan.

**What's kept in your team's folder:**

- Activity counts and rep names. Prospect names, emails, phone numbers, and companies are not kept
- Any downloaded files you leave in there. You can delete them whenever you like
- Coaching notes, as simple text files

**Please keep your team's folder private,** and out of shared drives. Coaching notes are sensitive.

**What SDR Manager won't do:**

- Send messages, or change anything in your sales tools
- Rank your reps against each other
- Recommend hiring, firing, pay, or formal performance action. If you ask, it gives you the facts and suggests involving HR
- Make up numbers. A built-in check stops Claude writing its own statistics into a report, so every number comes from your data, or from your own coaching notes
- Guess anyone's gender from their name. Reports are checked for this automatically. If Claude slips up in chat, just correct it

## Common questions

**The Code tab asks me to upgrade.**
You need a paid Claude plan to use the Code tab. If your company manages your account, ask your administrator.

**Claude doesn't know what SDR Manager is.**
Start a new session in the **Code** tab and try again. If Claude still doesn't know it, close the Claude app completely, open it again, and paste the [install message](#step-3-ask-claude-to-install-it) once more.

**Claude says Python is missing.**
It's free and safe to install:

- **Mac:** go to [python.org/downloads](https://www.python.org/downloads/), click the yellow **Download** button, open the file, and click through the installer.
- **Windows:** do the same, but tick **Add python.exe to PATH** on the first screen before you click **Install Now**.

Then close Claude, open it again, and carry on.

**On Windows, Claude says Git is required.**
Update the Claude app first, because recent versions no longer ask for this. If you still see the message, install [Git for Windows](https://git-scm.com/download/win) and accept the default options. It's a free program, and you won't need to use it yourself.

**Claude keeps asking for permission. Is that normal?**
Yes. Claude checks with you before it runs anything on your computer or changes a file. For SDR Manager, these requests are its calculator and report builder, so it's fine to allow them. If you'd like fewer pop-ups, use the mode button just under the message box. **Accept edits** stops the questions about saving files, and **Auto**, if you see it, stops most of the others.

**I got a web page instead of a PDF.**
That means it couldn't find Chrome or Edge. Open the file in any browser, choose **Print**, then choose **Save as PDF**.

**My Excel file won't open.**
In Excel, choose **Save As**, pick **CSV**, then try again.

**Can I use the Chat or Cowork tab instead of the Code tab?**
Not yet. SDR Manager has only been tested in the Code tab, and the install above is made for it.

**Why does it say "Not enough data"?**
Claude won't judge a rep on just a few calls or meetings, because that wouldn't be fair. Download more weeks and try again.

**Why does the report say "Partial week"?**
Your files stop before the end of the week. It's fine to use, or you can download them again once the week is over.

**Every rep has the same problem. What does that mean?**
The report calls this a team pattern. When everyone struggles at the same step, look at the prospect list, the messaging, or the targets before coaching each rep.

**How do I change the name on the reports?**
Reports are branded Andy Gheewalla. To use your own name, ask whoever looks after your technical setup to follow the [technical guide](docs/technical-guide.md).

**How do I update SDR Manager?**
Paste the [install message](#step-3-ask-claude-to-install-it) again. Your team's folder and reports aren't touched.

**How do I remove SDR Manager?**
Paste this into the **Code** tab. Your team's folder and reports stay on your computer.

```text
Please remove SDR Manager from this computer. Download
https://github.com/mangollc/claude-SDR-Manager-plugin and follow the
"Update or remove" section of docs/technical-guide.md.
```

**Something else went wrong.**
Tell Claude what happened in your own words. It can usually work it out. If not, [let us know here](https://github.com/mangollc/claude-SDR-Manager-plugin/issues).

## What's been tested

We want to be upfront about this, because the plugin is new.

| Area | Status |
|---|---|
| Reports, coaching focus, and 1:1 sheets | Tested in full with the sample team |
| Installing it with the message above, on a Mac | Tested in full, using the Claude Code built into the Claude app |
| Using it in plain English, on a Mac | Tested in full, using the Claude Code built into the Claude app |
| Installing it from GitHub with Claude Code commands | Tested in full |
| Adding it through the Claude app's Plugins screen | **Not working in our test.** Every click worked, but SDR Manager never reached the Code tab |
| Cowork | **Not tested yet** |
| Windows | **Not tested yet** |
| Cursor, Codex, and VS Code with Copilot | **Not tested in full.** Their official guides confirm how skills are installed |
| Gemini CLI | Confirmed it finds SDR Manager, but not tested in full |
| Real company files | **Not tested yet.** Tested with deliberately messy sample files |

If you try something from this list, please [tell us how it went](https://github.com/mangollc/claude-SDR-Manager-plugin/issues).

## Technical details

If you're in IT, you're a developer, or you'd rather install it by hand, see the [technical guide](docs/technical-guide.md).

## What's coming next

- **Next:** review your outreach sequences, rewrite weak emails and call scripts, check email deliverability, and flag legal limits
- **After that:** new-hire onboarding plans, cold call practice, and call scoring
- **Later:** team schedules, prospect journey maps, leadership slides, capacity planning, and direct connections to sales tools

Not included yet: inbound leads, pipeline value, and commission.

## License

[MIT](LICENSE). You're free to use it, change it, and share it.
