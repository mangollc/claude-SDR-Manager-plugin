# sdr-rewrite: Stage 2 First Piece Design

- **Date:** 2026-10-31
- **Status:** Built, and tested in real sessions on made-up messages. Sections 7 to 10 changed after review, as noted there
- **Command:** `/sdr-rewrite` from the paste-in install, `/sdr-manager:rewrite` from the plugin
- **Version:** 0.2.0
- **Builds on:** [the first build design](2026-10-30-sdr-manager-design.md)

## 1. Summary

A manager pastes one weak email, cold call script, or LinkedIn message and gets a stronger version, ready to copy into their sales tool.

Claude writes the new version. The program then checks it and saves it only if it passes. The plugin's value over plain Claude is that it knows the team's product and customer, and the program rejects drafts that break a placeholder, drop a legal line, or add a made-up number.

## 2. Where this fits in stage 2

Stage 2 has four pieces. Each gets its own design and build.

| Piece | Status | What's known |
|---|---|---|
| Rewrite outreach | This design | Needs no new files |
| Cadence review | Later | Step results aren't always downloadable. [Outreach's report](https://support.outreach.io/support/solutions/articles/159000423739-outreach-insights-sequence-performance-report-overview) has a CSV download, though step-level content is unconfirmed. [HubSpot's help page](https://knowledge.hubspot.com/sequences/analyze-sequence-enrollment-and-performance-data) mentions no download, and its users have asked for one. So this piece can't depend on a file |
| Email deliverability check | Later | Stored counts show warning signs only, because exports can't see the spam folder. Checking a company's email setup means looking up public records online, which would change the "no network calls" promise. The owner must approve that first |
| Legal limits | Later | Flags and "ask your lawyer", never "this is legal". This piece's checks cover the basics, and country-specific rules wait |

No working SDR manager is available to test with yet, so this design relies on public help pages and made-up sample messages. The README must keep saying so.

## 3. Decisions

| Topic | Decision |
|---|---|
| First piece | Rewrite outreach, chosen by the owner |
| Channels | Email, cold calls, and LinkedIn, all in this build |
| Approach | Claude writes and the program checks, because skill rules alone were skipped in testing |
| Facts | Claude may only use the original, the team profile, and saved proof points |
| Output | Chat plus a `.txt` file, because a rewrite must be copied into a sales tool |
| Originals | Held in the draft only while it's being checked, then deleted, so a pasted email with prospect details doesn't stay on disk |
| Versions | One rewrite at a time. The manager can ask for changes |
| Team folder | Required. With no folder, the skill sends the manager to setup |
| Limits on Claude | Unchanged. It never sends anything or changes anything in a sales tool |

**Proof points** are true results or customer names that reps may mention. The manager supplies them.

## 4. Manager experience

The manager says one of these and pastes the message:

- "Rewrite this email."
- "Rewrite this call script."
- "Rewrite this LinkedIn message."
- "Rewrite our first email."
- "Rewrite the sample email."

Pasted rough notes count as an original, so there's no separate way to write from nothing.

1. Run `status` to find the team's folder. If it exits with code 2, or the profile has no `product`, send the manager to setup. If `leftover_draft` is set, delete it with `discard-draft`.
2. Read `team-profile.json` and `references/outreach-playbook.md`.
3. Get the message. Remind the manager to paste the template, not a sent email, so prospect details stay out.
4. Ask at most two things:
   - What the message is, if that isn't clear
   - Once per team, when the profile has no `proof_points` key, which true results or customer names reps may mention. Save the answers to `team-profile.json`. If there are none, save an empty list, so the question isn't asked again
5. Write the draft to `outreach/draft.json` in the team's folder, then run `check-outreach`.
6. Fix every problem and check again. Never work around a failed check. If the manager stops, or a problem can't be fixed, run `discard-draft`.
7. Show the before and after, why it changed, anything to confirm, where it was saved, and a next step.
8. Finish with a fixed paragraph: read it before using it, these checks aren't legal advice, and the scorecard will show replies over time but can't say which message caused a change. Real sessions dropped a point when asked to use their own words, so the skill gives the exact text.

If the manager asks for a change, write a new draft and run the check again. The same name on the same day replaces the earlier file.

Claude follows the existing skill rules: everyday words, a sentence to type as the next step, and no commands or file formats unless asked.

## 5. Architecture

```text
Pasted message + team profile + outreach playbook
      │
      ▼
Claude writes outreach/draft.json
      │
      ▼
check-outreach ──► problems: fix the draft and check again
      │
      ▼ passes
outreach/<date>-<name>.txt saved, draft deleted
```

| File | Change |
|---|---|
| `skills/rewrite/SKILL.md` | New |
| `references/outreach-playbook.md` | New. What good looks like per channel, with dated sources |
| `assets/outreach-limits.json` | New. Starting limits with sources |
| `scripts/sdrlib/outreach.py` | New. The checks and the saved file |
| `scripts/sdr.py` | Add `check-outreach --workspace W --draft F` |
| `scripts/sdrlib/profile.py` | Validate `proof_points` and `outreach_limits` |
| `skills/setup/SKILL.md` | Offer to collect proof points |
| `skills/scorecard/SKILL.md` | Suggest "Rewrite our first email." when `team_pattern.step` is 2 or 3 |
| `sample-data/team-profile.json`, `tests/make_sample_data.py` | Add made-up proof points |
| `sample-data/outreach/` | New. Three deliberately weak messages |
| `install.py` | Add `rewrite` to `SKILLS` |
| `tests/` | New tests, and `rewrite` added to the skill lists |
| `README.md`, `docs/technical-guide.md` | New command, privacy notes, test status, and roadmap |
| `.claude-plugin/plugin.json` | Version 0.2.0 |

The skill reads sample messages from `${CLAUDE_PLUGIN_ROOT}/sample-data/outreach/`, which works in both install routes.

## 6. Draft file

```json
{
  "kind": "first_email",
  "name": "New customer email 1",
  "original": "The message as pasted",
  "subject": "Inventory planning at {{company}}",
  "body": "The new message, without its footer",
  "footer": "Signature, opt-out line, and postal address",
  "changes": ["Why it changed, in words"]
}
```

- `kind` is one of `first_email`, `follow_up_email`, `call_script`, `linkedin_note`, or `linkedin_message`.
- `subject` applies to email only, and may be blank for a follow-up in the same thread.
- `footer` is optional. It doesn't count toward length limits.

## 7. Checks

**Approved sources** are `original`, plus `company`, `product`, `ideal_customer`, and `proof_points` from the profile.

**The new message** is `subject`, `body`, and `footer` together. Placeholders are removed before checking numbers and names.

**How protected text is recognized:**

- **Opt-out:** wording aimed at the reader, such as unsubscribe, opt out of these emails, stop receiving these emails, prefer not to receive, or remove you from our list. "Stop getting surprised by stockouts" and "unsubscribe rates" don't count
- **Call-recording notice:** a statement that this call, conversation, or line is or may be recorded, or a request to record it, so a product that records calls isn't caught
- **Postal address:** a P.O. Box, a number followed by a capitalized street word that ends the address, a suite or floor number, a US state and ZIP code, or a UK postcode

A pasted `Subject:` line is never protected. The skill also tells Claude to keep any line that tells the reader how to stop hearing from them, however it's worded, because the program can't recognize every wording.

### 7.1 Rejected

| Rule | Details |
|---|---|
| Placeholders | If the original has any, the new message must contain exactly the same set, spelled the same. Recognize `{{...}}` including spaces, dots, and fallbacks such as `{{first_name\|there}}`, plus `{{{...}}}`, `{!...}`, `${...}`, `{word}`, `[[...]]`, `[...]`, `<<...>>`, `*\|...\|*`, `%word%`, and `%%word%%` |
| Protected text | Each sentence or line of the original that holds an opt-out, a call-recording notice, or a postal address must appear unchanged |
| New numbers | Every number must appear in an approved source. Clock times are allowed, and so is time the rep asks for, such as "a 15-minute call" or "Got 30 seconds?". "Saves 40 hours a week" is a claim, so it needs a source. Digits inside a new placeholder count, so `[10x faster]` is rejected. `extract_numbers` from `narrative_check.py` can't be reused here, because it misses `10x` and `$2M`, the claims most likely to be made up. `outreach.py` finds any run of digits that doesn't sit inside a word, so `B2B` and `Q3` are left alone |
| Length | See section 7.3 |
| Honest first contact | For `first_email`, `linkedin_note`, and `call_script`: no subject starting with `Re:`, `Fwd:`, or `Fw:`, and no claim of a past conversation, such as "as we discussed", "per our conversation", or "following up on our last call". Lines that are honest on a live call, such as "thanks for taking my call", are allowed |
| Contact details in labels | No email address or phone number in `name` or `changes` |
| Why it changed | `changes` goes through `check_narrative`, which rejects statistics and gendered pronouns |

### 7.2 Manager confirms

These don't stop the save. Claude must show each one.

| Rule | Details |
|---|---|
| New names | A capitalized word mid-sentence that isn't in an approved source, leaving out days and months |
| Spelled-out numbers | Number words that aren't in an approved source, using `extract_number_words`, plus words such as "doubled", "tenfold", "hundreds", and "zero" |
| New placeholders | Only when the original has none. Ask whether they match how the sales tool writes them |
| Contact details in the message | An email address or phone number in `subject` or `body`, which may be a prospect's. A signature in `footer` isn't questioned |
| Missing opt-out | For email, when no opt-out shows and no placeholder such as `{{unsubscribe_link}}` could supply one |
| Missing postal address | For email, when none shows and no placeholder such as `{{postal_address}}` could supply one. `{{company.address}}` doesn't count, because that's the prospect's |
| Assumed footer | For email, when one of those is missing and a `{{signature}}` or `{{footer}}` placeholder might supply it. Name the placeholder and ask |

### 7.3 Starting limits

These live in `assets/outreach-limits.json`. A team can replace one under `outreach_limits` in its profile, in the same shape as `targets`, and it then shows `source: "team"`.

| Kind | Limit | Source |
|---|---|---|
| `first_email` | 80 words | [Instantly 2026](https://instantly.ai/cold-email-benchmark-report-2026): best campaigns stayed under 80 |
| `follow_up_email` | 125 words | Plugin default, based on vendor studies |
| `call_script` | 150 words | Plugin default, about a minute of talking |
| `linkedin_note` | 200 characters | [LinkedIn Help](https://www.linkedin.com/help/linkedin/answer/a563153): the limit for a note |
| `linkedin_message` | 100 words | Plugin default |

Limits count `body` only, and each placeholder counts as written. A Premium LinkedIn team can raise `linkedin_note` to 300.

## 8. Command output

**Passes (exit 0):** saves the file, deletes the draft, and prints:

```json
{
  "status": "ok",
  "path": "/full/path/outreach/2026-10-31-new-customer-email-1.txt",
  "length": {"value": 62, "limit": 80, "unit": "words", "source": "Instantly 2026"},
  "to_confirm": [{"rule": "new_name", "text": "Salesforce"}]
}
```

**Fails (exit 2):** saves nothing and keeps the draft:

```json
{
  "status": "needs_input",
  "problems": [{"rule": "placeholder_changed", "text": "{{firstName}}"}]
}
```

**Saved file:** a UTF-8 `.txt`, named `<date>-<slug>.txt` using `rep_slug`:

```text
Email, first message
Name: New customer email 1
Saved: 2026-10-31

Subject: Inventory planning at {{company}}

{{first_name}}, how does {{company}} plan inventory across stores today?

Why it changed
- It opens with their problem instead of your company

Please confirm
- "Salesforce" is new in this version. Is that accurate?
```

## 9. Error handling

| Situation | Behavior |
|---|---|
| No team folder, or no `product` in the profile | Send the manager to setup |
| Draft file missing or not valid JSON | Exit with a plain message, and Claude writes it again |
| Rewrite abandoned, or a problem can't be fixed | Claude runs `discard-draft`, and tells the manager what stopped it. If that doesn't happen, `status` reports `leftover_draft`, and the next rewrite deletes it |
| A very long `name` | Shorten the file name |
| Unknown `kind`, or a missing `name`, `original`, or `body` | Exit 2 with a plain message |
| `proof_points` isn't a list of text, or a limit isn't a positive number | `ProfileError` with a plain message |
| No `outreach` folder in an older workspace | Create it on save |
| Manager wants a protected line changed | Explain that it stays in the rewrite, and that they can change it in their sales tool |
| Manager asks about a country's law | Say that country-specific rules aren't covered yet, and suggest a lawyer |

## 10. Privacy and safety

- Pasted messages and proof points go to the AI tool's provider, like everything else read in chat. The README and technical guide must say so.
- The saved file holds the new version only. The draft, which holds the original, is deleted on success, and by `discard-draft` otherwise.
- A sent email's details can still reach the saved file if Claude copies them. The skill forbids it, and the program questions any email address or phone number in the message.
- The team's `.gitignore` already covers the new folder.
- Claude never invents facts, customers, or familiarity with a prospect, such as "I loved your recent post". The program can't catch every case, so the skill states the rule too.
- Checks catch common problems. They aren't legal advice, and the skill and README say so.
- The manager stays responsible for reading a rewrite before using it, because the program can't catch a reworded claim such as "cuts stockouts".

## 11. Testing

**Unit tests, written first:**

- Every rule in sections 7.1 and 7.2, passing and failing
- Placeholders in each format, including a fallback and a changed spelling
- Opt-outs and addresses inside a paragraph as well as on their own line
- Allowed meeting lengths, and numbers that only appear in proof points
- Team limit overrides
- The saved file, the draft's removal, and replacing a same-day file

**Real sessions:** on Haiku, using the README's exact sentences, for all three channels. Traps:

- A first email with a fake `Re:` subject
- An email with no facts to lean on, which tempts Claude to invent some
- `{{contact.firstname}}` and `{!Contact.FirstName}` in the same run
- An email with an opt-out line and a postal address in its footer
- A LinkedIn note far over the limit

Check that each session keeps to everyday words, saves in the team's folder, and asks no more than two questions.

**Both install routes:** test the plugin and `install.py`, since `install.py` copies the skills differently.

## 12. Success criteria

1. A manager gets a checked rewrite from a paste, with no more than two questions.
2. In real sessions, no saved rewrite changes a placeholder, drops protected text, adds a number, or goes over a limit.
3. A rewrite needs about four permission approvals in Manual mode, against 15 to 20 for a first scorecard.
4. All existing tests still pass, and the new code has at least 80% coverage.
5. The README states that this was tested on made-up messages only.

## 13. Sources

Checked on 2026-10-31. The outreach playbook repeats these, with dates, and adds any it needs.

- [FTC, CAN-SPAM Act: A Compliance Guide for Business](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business): no exception for business email, postal address, opt-out, and penalties up to $53,088 per email.
- [FTC, Candid answers to CAN-SPAM questions](https://www.ftc.gov/business-guidance/blog/2015/08/candid-answers-can-spam-questions): deceptive subject lines are illegal.
- [Instantly, Cold Email Benchmark Report 2026](https://instantly.ai/cold-email-benchmark-report-2026): best campaigns stayed under 80 words.
- [Gong Labs, cold call opening lines](https://www.gong.io/blog/cold-call-opening-lines), April 2018, 90,380 calls: stating the reason for the call made success 2.1 times more likely, and "Did I catch you at a bad time?" scored worst.
- [Gong Labs, best and worst openers](https://www.gong.io/blog/the-best-and-worst-cold-call-openers-backed-by-data-from-300m-calls), July 2024, 300M+ calls: "Did I catch you at a bad time?" still scored lowest, and permission-based openers scored far higher. Both studies agree on what to avoid, so the playbook uses that. "How have you been?" scored well in 2018, but it implies a familiarity that doesn't exist, so the playbook rules it out.
- [LinkedIn Help, Personalize invitations to connect](https://www.linkedin.com/help/linkedin/answer/a563153): read in a browser on 2026-10-31. Notes can be up to 200 characters, free accounts get up to three a month, and Premium members can personalize all invitations. Premium's 300-character figure comes from secondary sources.
- [Salesforce Help, Handlebars merge language](https://help.salesforce.com/s/articleView?language=en_US&id=sales.handlebars_template_language.htm&type=5): `{{{Recipient.FirstName}}}`.
- [HubSpot, personalization tokens](https://knowledge.hubspot.com/marketing-email/use-personalization-tokens) and [Instantly, dynamic fields](https://instantly.ai/blog/using-crm-fields-for-dynamic-cold-email-personalization/): other placeholder formats. Salesforce's older `{!Contact.FirstName}` format comes from memory, and recognizing it does no harm if it's rarely seen.
