---
name: macos-calendar-plus
description: Create, list, and manage macOS Calendar events with location support via AppleScript. Use when the user asks to add a reminder, schedule an event, create a calendar entry, set a deadline, or anything involving Apple Calendar on macOS. Triggers on requests like "remind me in 3 days", "add to my calendar", "schedule a meeting next Monday at 2pm", "create a recurring weekly event", "add event at [place/address]". Supports setting event location (street address format only — look up addresses from place names before creating events). macOS only.
license: MIT
compatibility: Requires macOS with Calendar.app. Uses osascript (AppleScript) and python3 for JSON parsing.
metadata:
  author: axot
  version: "1.0.0"
  based_on: lucaperret/agent-skills@macos-calendar v1.2.0
  openclaw:
    os: macos
    emoji: "\U0001F4C5"
    requires:
      bins:
        - osascript
        - python3
---

# macOS Calendar Plus

Manage Apple Calendar events (with location support) via `$SKILL_DIR/scripts/calendar.sh`. All date handling uses relative math (`current date + N * days`) to avoid locale issues.

## Quick start

### List calendars

Always list calendars first to find the correct calendar name:

```bash
"$SKILL_DIR/scripts/calendar.sh" list-calendars
```

### Create an event

```bash
echo '<json>' | "$SKILL_DIR/scripts/calendar.sh" create-event
```

JSON fields:

| Field | Required | Default | Description |
|---|---|---|---|
| `summary` | yes | - | Event title |
| `calendar` | no | first calendar | Calendar name (from list-calendars) |
| `description` | no | "" | Event notes |
| `location` | no | "" | Event location — **street address only** (see "Location rules" section) |
| `offset_days` | no | 0 | Days from today (0=today, 1=tomorrow, 7=next week) |
| `iso_date` | no | - | Absolute date `YYYY-MM-DD` (overrides offset_days) |
| `hour` | no | 9 | Start hour (0-23) |
| `minute` | no | 0 | Start minute (0-59) |
| `duration_minutes` | no | 30 | Duration |
| `alarm_minutes` | no | 0 | Alert N minutes before (0=no alarm) |
| `all_day` | no | false | All-day event |
| `recurrence` | no | - | iCal RRULE string. See [references/recurrence.md](references/recurrence.md) |

## Interpreting natural language

Map user requests to JSON fields:

| User says | JSON |
|---|---|
| "tomorrow at 2pm" | `offset_days: 1, hour: 14` |
| "in 3 days" | `offset_days: 3` |
| "next Monday at 10am" | Calculate offset_days from today to next Monday, `hour: 10` |
| "February 25 at 3:30pm" | `iso_date: "2026-02-25", hour: 15, minute: 30` |
| "every weekday at 9am" | `hour: 9, recurrence: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"` |
| "remind me 1 hour before" | `alarm_minutes: 60` |
| "all day event on March 1" | `iso_date: "2026-03-01", all_day: true` |
| "meeting at Starbucks Shibuya" | Search web for address → `location: "21-6, Udagawacho, Shibuya, Tokyo, Japan"` |
| "dentist at 東京都渋谷区..." | Convert to English address format → `location: "..., Shibuya, Tokyo, Japan"` |

For "next Monday", "next Friday" etc: compute the day offset using the current date. Use `date` command if needed:

```bash
target=1; today=$(date +%u); offset=$(( (target - today + 7) % 7 )); [ "$offset" -eq 0 ] && offset=7; echo $offset
```

## Example prompts

**"Remind me to call the dentist in 2 days"**
```bash
"$SKILL_DIR/scripts/calendar.sh" list-calendars
```
Then:
```bash
echo '{"calendar":"Personal","summary":"Call dentist","offset_days":2,"hour":9,"duration_minutes":15,"alarm_minutes":30}' | "$SKILL_DIR/scripts/calendar.sh" create-event
```

**"Schedule a team sync every Tuesday at 2pm at Tokyo Tower"**
```bash
echo '{"calendar":"Personal","summary":"Team sync","hour":14,"duration_minutes":60,"recurrence":"FREQ=WEEKLY;BYDAY=TU","alarm_minutes":10,"location":"4-2-8, Shibakoen, Minato, Tokyo, Japan"}' | "$SKILL_DIR/scripts/calendar.sh" create-event
```

**"Doctor appointment next Thursday at 3:30pm at Roppongi Hills, remind me 1 hour before"**
```bash
target=4; today=$(date +%u); offset=$(( (target - today + 7) % 7 )); [ "$offset" -eq 0 ] && offset=7
```
Then:
```bash
echo "{\"calendar\":\"Personal\",\"summary\":\"Doctor appointment\",\"offset_days\":$offset,\"hour\":15,\"minute\":30,\"duration_minutes\":60,\"alarm_minutes\":60,\"location\":\"6-10-1, Roppongi, Minato, Tokyo, Japan\"}" | "$SKILL_DIR/scripts/calendar.sh" create-event
```

**"Block July 15 as vacation — all day"**
```bash
echo '{"calendar":"Personal","summary":"Vacation","iso_date":"2026-07-15","all_day":true}' | "$SKILL_DIR/scripts/calendar.sh" create-event
```

## Critical rules

1. **Always list calendars first** if the user hasn't specified one — calendars marked `[read-only]` cannot be used for event creation
2. **Never use hardcoded date strings** in AppleScript — always use `offset_days` or `iso_date`
3. **Confirm the calendar name** with the user if multiple personal calendars exist
4. **Never target a `[read-only]` calendar** — the script will reject it with an error
5. **For recurring events**, consult [references/recurrence.md](references/recurrence.md) for RRULE syntax
6. **Pass JSON via stdin** — never as a CLI argument (avoids leaking data in process list)
7. **All fields are validated** by the script (type coercion, range checks, format validation) — invalid input is rejected with an error message
8. **All actions are logged** to `logs/calendar.log` with timestamp, command, calendar, and summary
9. **Location format is strict** — see "Location rules" section below.

## Location rules

The `location` field must be a **street address only**, formatted as:

```
{street/block number}, {area}, {city}, {prefecture}, Japan
```

**Example:** `156-2, Abu, Nago, Okinawa, Japan`

**What to strip:**
- Postal codes (〒xxx-xxxx)
- Place/brand/venue names (カヌチャリゾート, Starbucks, etc.)
- Building/floor names (Mori Tower 52F, QFRONT 2F, etc.)

**When the user gives only a place name** (e.g. "カヌチャベイホテル", "Starbucks Shibuya"), search the web — the venue's official site or maps — to find the actual street address before creating the event. Never use a place name as the location value.
