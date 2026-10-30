# Technical guide

This guide is for IT teams, developers, and AI assistants. If you're a sales manager, you probably want the [main guide](../README.md) instead.

## Contents

- [External services, API keys, and environment variables](#external-services-api-keys-and-environment-variables)
- [Instructions for AI assistants](#instructions-for-ai-assistants)
- [Install in Claude Code](#install-in-claude-code)
- [Install in other tools](#install-in-other-tools)
- [Update or remove](#update-or-remove)
- [Allowing it in a managed Claude organization](#allowing-it-in-a-managed-claude-organization)
- [Customizing](#customizing)
- [What gets sent where](#what-gets-sent-where)
- [How it's built](#how-its-built)
- [Command-line tool](#command-line-tool)
- [Tests](#tests)
- [Test status](#test-status)

## External services, API keys, and environment variables

**SDR Manager needs none of these.** The code was audited for network use before release.

| Question | Answer |
|---|---|
| API keys | **None** |
| Environment variables | **None** |
| External services or APIs | **None.** The program makes no network calls |
| Accounts to create | **None**, apart from the AI tool in use |
| Python packages to install | **None.** It uses the standard library |

**Local programs it uses:**

| Program | Why | Required? |
|---|---|---|
| Python 3.9 or newer | Runs the calculator and report builder | Yes |
| Chrome, Edge, Chromium, or Brave | Prints reports to PDF in headless mode. Reports load nothing from the internet | Optional. Without one, it keeps an HTML file |
| `openpyxl` | Reads `.xlsx` files | Optional. Without it, files need saving as CSV |

The AI tool is the only outside connection. It sends what it reads to its own provider. See [What gets sent where](#what-gets-sent-where).

## Instructions for AI assistants

A person asked you to install SDR Manager so it's available in all their projects. They may not be technical, so explain what you're doing in plain language, and don't assume they know what a terminal is.

1. **Check for Python 3.9 or newer.** Try `python3 --version`, then `python --version`, then `py -3 --version`. If none works, tell the person to install it from https://www.python.org/downloads/ and, on Windows, to tick **Add python.exe to PATH**. Stop until that's done.

2. **Download the code** to a temporary folder. Use `git clone https://github.com/mangollc/claude-SDR-Manager-plugin.git` if Git is available. Otherwise, download and unzip https://github.com/mangollc/claude-SDR-Manager-plugin/archive/refs/heads/main.zip.

3. **Run the installer** from inside that folder, using whichever Python command worked:

   | If you are | Run |
   |---|---|
   | Claude Code, or the Claude desktop app's Code tab | `python3 install.py --tool claude` |
   | Codex, Cursor, VS Code Copilot, Gemini CLI, or similar | `python3 install.py` |

4. **Confirm it worked.** The installer prints where it put the skills. Check that `sdr-setup/SKILL.md` exists in that folder.

5. **Delete the temporary folder.** The installer copied everything it needs to `~/.sdr-manager`.

6. **Tell the person** to close and reopen their AI tool, then say: *"Set up SDR Manager with the sample team."*

## Install in Claude Code

This installs for the user, so it's available in every project.

```bash
claude plugin marketplace add mangollc/claude-SDR-Manager-plugin
claude plugin install sdr-manager@mango-plugins
```

To do the same inside a session, start each line with `/plugin` instead of `claude plugin`.

Commands appear as `/sdr-manager:setup`, `/sdr-manager:scorecard`, and `/sdr-manager:one-on-one`.

## Install in other tools

### Mac

```bash
git clone https://github.com/mangollc/claude-SDR-Manager-plugin.git
cd claude-SDR-Manager-plugin
python3 install.py
```

### Windows (PowerShell)

```powershell
git clone https://github.com/mangollc/claude-SDR-Manager-plugin.git
cd claude-SDR-Manager-plugin
py -3 install.py
```

Then restart the AI tool.

### What the installer does

It generates standalone copies of the skills, because the originals rely on `${CLAUDE_PLUGIN_ROOT}`, which only Claude Code provides. It changes nothing else.

```text
 ~/.agents/skills/            Skills that AI tools read
   sdr-setup/
   sdr-scorecard/
   sdr-one-on-one/
 ~/.sdr-manager/              The program, copied here
```

On Windows, `~` means the user folder, such as `C:\Users\you`.

### Which folder each tool reads

| Tool | Command | Global folder | Source |
|---|---|---|---|
| Codex | `install.py` | `~/.agents/skills` | [OpenAI docs](https://developers.openai.com/codex/skills) |
| Cursor | `install.py` | `~/.agents/skills` | [Cursor docs](https://cursor.com/docs/skills) |
| VS Code with Copilot | `install.py` | `~/.agents/skills` | [VS Code docs](https://code.visualstudio.com/docs/agent-customization/agent-skills) |
| Gemini CLI | `install.py` | `~/.agents/skills` | Confirmed by test |
| Claude Code, without the plugin | `install.py --tool claude` | `~/.claude/skills` | Tested in a real session |
| Any other tool with a skills folder | `install.py --skills-dir <folder>` | The folder given | |

Install to one folder per tool, because Cursor and VS Code also read `~/.claude/skills`, and would otherwise see two copies.

For a tool with no skills feature, install with `install.py`, then tell it: *"Follow the instructions in `~/.agents/skills/sdr-scorecard/SKILL.md`."*

## Update or remove

| Task | Claude Code plugin | `install.py` |
|---|---|---|
| Update | `claude plugin update sdr-manager@mango-plugins` | `git pull`, then run `install.py` again |
| Remove | `claude plugin uninstall sdr-manager@mango-plugins` | `install.py --uninstall` |

Removing it never touches a team's workspace folder. If you used `--tool` or `--skills-dir`, pass the same option to `--uninstall`.

## Allowing it in a managed Claude organization

On Team and Enterprise plans, an owner can limit which marketplaces members can add. To allow it, add `mangollc/claude-SDR-Manager-plugin` as a permitted source, or distribute it to your organization as a plugin. See Anthropic's [Manage plugins for your organization](https://support.claude.com/en/articles/13837433-manage-plugins-for-your-organization).

## Customizing

| To change | Edit |
|---|---|
| Report brand name | `name` in `assets/brand.json` |
| Report appearance | `assets/templates/report.css` |
| Coaching advice | `references/coaching-playbook.md` |
| Starting targets | `assets/default-targets.json` |

For the Claude Code plugin, fork the repository first, then install from your fork, or your changes will be lost on update.

A team can replace any target without editing files, by asking the assistant to change it. Those changes are stored in the team's own `team-profile.json`.

## What gets sent where

**Read locally only:** full export files. `sdr.py inspect` gives the assistant column names, row counts, up to 10 masked lines, and the distinct values of small, non-sensitive columns. Columns with prospect details or free text are masked, and so is any value that looks like an email address or phone number.

**Read by the AI tool, and sent to its provider:** those previews, `team-profile.json`, the metrics JSON, coaching notes during 1:1 work, and anything typed in chat.

**Stored in the workspace:** daily counts per rep, meeting rows without prospect details, generated reports, coaching notes, saved column mappings, and any exports left in `imports/`. The workspace has a `.gitignore` containing `*`.

## How it's built

Skills hold the judgment, and scripts hold the math. Claude's written text can't state statistics, because `narrative_check.py` rejects them.

```text
.claude-plugin/   Plugin and marketplace manifests
skills/           setup, scorecard, one-on-one
references/       Coaching playbook, metric definitions, file mapping guide
scripts/          sdr.py and the sdrlib package (standard library only)
assets/           Starting targets, brand, and report templates
sample-data/      The made-up team and messy exports
install.py        Installer for tools other than the Claude Code plugin
tests/            Test suite
docs/             This guide, the design spec, and the build plan
```

```text
exports ─► inspect ─► confirmed mapping ─► normalize ─► daily counts
                                                            │
        PDF ◄─ report ◄─ check-narrative ◄─ Claude's text ◄─ metrics
```

The design is explained in the [spec](superpowers/specs/2026-10-30-sdr-manager-design.md).

## Command-line tool

Skills call `scripts/sdr.py`. Every command prints JSON. Exit codes: 0 success, 1 unexpected error, 2 the manager must decide something, 3 Python too old.

| Command | Purpose |
|---|---|
| `check-env` | Report Python, `openpyxl`, and browser availability |
| `init-workspace --path P [--sample]` | Create a workspace |
| `status [--workspace W]` | Find the workspace and latest scorecard |
| `targets --workspace W` | Validate the profile and print resolved targets |
| `inspect FILE [--header-row N] [--workspace W]` | Print a masked preview |
| `normalize --workspace W --files F... [--week W]` | Store counts, or report what's blocking |
| `metrics --workspace W [--week W]` | Build the metrics file, once the week's time off is saved |
| `check-narrative --workspace W --narrative F [--rep NAME]` | Reject statistics in written text |
| `report team --workspace W --week W --narrative F` | Build the team PDF |
| `report one-on-one --workspace W --week W --rep NAME --narrative F` | Build the 1:1 PDF |
| `log-coaching --workspace W --rep NAME --entry-file F` | Add a coaching entry |

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

The tests need nothing installed. To regenerate the sample data, run `python3 tests/make_sample_data.py`.

## Test status

| Area | Status |
|---|---|
| Claude Code plugin on macOS | Tested end to end with real sessions, including install from GitHub |
| Standalone skills from `install.py` | Tested end to end in a real session |
| Python 3.9 and 3.12 | Over 450 automated tests pass, with 97% coverage of `scripts/` |
| PDF creation with Chrome | Tested |
| Gemini CLI | Confirmed it discovers the skills. No full session has been run |
| Codex, Cursor, and VS Code Copilot | Folder confirmed from official docs. No full session has been run |
| Adding through the Claude app's Plugins screen | Not tested. Steps come from Anthropic's help center |
| Windows and Linux | Not tested |
| Edge, Chromium, and Brave for PDFs | Not tested |
| Cowork | Not tested. Its sandbox may lack a browser, in which case reports stay as HTML |
| Real company exports | Not tested. Tested with deliberately messy sample files |
