# File mapping guide

A mapping tells the plugin what an export's columns mean. Each file type gets one mapping, saved in the workspace's `mappings/` folder and reused automatically when the columns match.

## Fields

| Field | Meaning |
|---|---|
| `signature` | Copy from `inspect` |
| `header_row` | Copy from `inspect`. Check it against `preview`, then re-run with `--header-row` if it's wrong |
| `kind` | `activities`, `rep_summary`, or `meetings` |
| `date_format` | A Python date format that matches the file exactly, such as `%m/%d/%Y` |
| `columns` | Which source column fills each standard field |
| `fixed` | A value that applies to every row, such as `{"action": "dial"}` |
| `values` | Translates source values into standard values |
| `flags` | Which values count as connected, replied, bounced, or accepted |

Common date formats:

| Example | Format |
|---|---|
| `10/26/2026` | `%m/%d/%Y` |
| `26/10/2026` | `%d/%m/%Y` |
| `2026-10-26` | `%Y-%m-%d` |
| `2026-10-26 09:14` | `%Y-%m-%d %H:%M` |
| `2026-10-26 09:14:30` | `%Y-%m-%d %H:%M:%S` |

Check day and month order against several rows, especially in non-US files.

## Activities: one row per touch

Every row needs a standard `action`, set by `fixed` or by a column with `values`.

| Action | Means |
|---|---|
| `dial` | A call attempt |
| `email` | An email sent |
| `email_reply` | A row that is itself a reply |
| `email_bounce` | A row that is itself a bounce |
| `li_request` | A LinkedIn connection request |
| `li_accept` | A row that is itself an accepted request |
| `li_message` | A LinkedIn message |
| `li_reply` | A row that is itself a LinkedIn reply |
| `li_other` | Any other LinkedIn touch, such as a profile view |
| `skip` | Not outreach, such as a note or task. The row is ignored |

Flags apply to these actions:

| Action | Flags |
|---|---|
| `dial` | `connected` |
| `email` | `replied`, `bounced` |
| `li_request` | `accepted` |
| `li_message` | `replied` |

A flag lists its values:

```json
{"column": "Call Result", "true": ["Connected"], "false": ["No Answer", "Voicemail"]}
```

When any filled cell counts, such as a `Replied At` timestamp, use:

```json
{"column": "Replied At", "any": true}
```

A blank cell always counts as false. Any other value that isn't listed stops the import, so a new call outcome is never silently treated as a miss.

### Example: a call log

```json
{
  "signature": "copied from inspect",
  "kind": "activities",
  "header_row": 3,
  "date_format": "%m/%d/%Y",
  "columns": {"date": "Activity Date", "rep": "Assigned To"},
  "fixed": {"action": "dial"},
  "flags": {
    "connected": {
      "column": "Call Result",
      "true": ["Connected"],
      "false": ["No Answer", "Voicemail", "Busy"]
    }
  }
}
```

### Example: one file with mixed activity

```json
{
  "signature": "copied from inspect",
  "kind": "activities",
  "header_row": 1,
  "date_format": "%Y-%m-%d",
  "columns": {"date": "Date", "rep": "Owner", "action": "Type"},
  "values": {
    "action": {"Call": "dial", "Email": "email", "Note": "skip", "Task": "skip"}
  },
  "flags": {
    "connected": {"column": "Outcome", "true": ["Connected"], "false": ["No Answer"]}
  }
}
```

## Rep summary: one row per rep per week

Use this when a tool only offers totals. Each row must cover exactly one week. If it covers longer, ask for a weekly version.

Add `week_start`, `rep`, and any of these count columns: `dials`, `connected`, `emails`, `replies`, `bounces`, `li_requests`, `li_accepted`, `li_messages`, `li_replies`, `li_other`.

```json
{
  "signature": "copied from inspect",
  "kind": "rep_summary",
  "header_row": 1,
  "date_format": "%Y-%m-%d",
  "columns": {
    "week_start": "Week Of",
    "rep": "Rep",
    "dials": "Calls",
    "connected": "Connects",
    "emails": "Emails Sent",
    "replies": "Replies"
  }
}
```

Days active isn't available from summary data.

## Meetings: one row per meeting

Use the columns `rep`, `booked_date`, `due_date`, `status`, and optionally `accepted`.

Standard statuses are `held`, `no_show`, `cancelled`, `rescheduled`, and `scheduled`. Standard acceptance values are `yes`, `no`, and `pending`. A blank acceptance cell counts as pending.

```json
{
  "signature": "copied from inspect",
  "kind": "meetings",
  "header_row": 1,
  "date_format": "%m/%d/%Y",
  "columns": {
    "rep": "Owner Name",
    "booked_date": "Date Booked",
    "due_date": "Meeting Date",
    "status": "Meeting Status",
    "accepted": "AE Decision"
  },
  "values": {
    "status": {
      "Completed": "held",
      "No Show": "no_show",
      "Cancelled": "cancelled",
      "Moved": "rescheduled",
      "Scheduled": "scheduled"
    },
    "accepted": {"Accepted": "yes", "Rejected": "no"}
  }
}
```

If there's no acceptance column, leave `accepted` out. Step 5 then shows as Not available.

## Common quirks

- **Report lines above the header:** `inspect` looks for the real header row. Check `header_row` against `preview`.
- **Totals at the bottom:** these rows are rejected and counted, which is expected.
- **Timestamps:** include the time in `date_format`.
- **Separate reply rows:** some tools log a reply as its own row. Map it to `email_reply`, not to a flag.
- **Rep emails instead of names:** add the address to the rep's `aliases`.
- **Calls logged in two tools:** use one file for each channel. Prefer the dialer, then the sequencer, then the CRM.
- **Non-outreach rows:** map notes, tasks, and calendar items to `skip`.
