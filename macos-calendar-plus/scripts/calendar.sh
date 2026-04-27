#!/bin/bash
# macOS Calendar helper via AppleScript (with location support)
# Usage: calendar.sh <command>
#
# Commands:
#   list-calendars              List all available calendars
#   list-events                 List events in a date range (reads stdin JSON)
#   create-event                Create an event from JSON (reads stdin)
#   batch-create                Create multiple events from JSON array (reads stdin)
#   update-event                Update an existing event (reads stdin JSON)

set -euo pipefail

# Verify required dependencies are available
for bin in osascript python3; do
  command -v "$bin" >/dev/null 2>&1 || { echo "Error: $bin is required but not found" >&2; exit 1; }
done

# Ensure Calendar.app is running (avoids AppleScript error -600)
if ! pgrep -q "Calendar"; then
  open -a Calendar
  sleep 2
fi

LOGFILE="${SKILL_DIR:-$(dirname "$0")/..}/logs/calendar.log"

# SR-004: Append-only action log
log_action() {
  mkdir -p "$(dirname "$LOGFILE")"
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "$3" >> "$LOGFILE"
}

cmd="${1:-help}"

case "$cmd" in
  list-calendars)
    osascript -e 'tell application "Calendar"
      set output to ""
      repeat with c in calendars
        if writable of c then
          set output to output & name of c & linefeed
        else
          set output to output & name of c & " [read-only]" & linefeed
        end if
      end repeat
      return output
    end tell'
    log_action "list-calendars" "-" "-"
    ;;

  list-events)
    json=$(cat)

    validated=$(CALENDAR_JSON="$json" python3 << 'PYEOF'
import os, sys, json

try:
    data = json.loads(os.environ['CALENDAR_JSON'])
except json.JSONDecodeError as e:
    print(f"Error: invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)

calendar = str(data.get('calendar', ''))
from_date = str(data.get('from_date', ''))
to_date = str(data.get('to_date', ''))

if not from_date or not to_date:
    print("Error: 'from_date' and 'to_date' are required (YYYY-MM-DD)", file=sys.stderr)
    sys.exit(1)

for name, val in [('from_date', from_date), ('to_date', to_date)]:
    parts = val.split('-')
    if len(parts) != 3:
        print(f"Error: {name} must be YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        if not (1 <= m <= 12 and 1 <= d <= 31 and y >= 1):
            print(f"Error: {name} has invalid date values", file=sys.stderr)
            sys.exit(1)
        if name == 'from_date':
            from_date = f"{y:04d}-{m:02d}-{d:02d}"
        else:
            to_date = f"{y:04d}-{m:02d}-{d:02d}"
    except ValueError:
        print(f"Error: {name} must contain numeric values", file=sys.stderr)
        sys.exit(1)

print(calendar)
print(from_date)
print(to_date)
PYEOF
    )

    {
      read -r calendar
      read -r from_date
      read -r to_date
    } <<< "$validated"

    result=$(osascript - "$calendar" "$from_date" "$to_date" <<'APPLESCRIPT'
on run argv
    set calName to item 1 of argv
    set fromISO to item 2 of argv
    set toISO to item 3 of argv

    set fromDate to current date
    set year of fromDate to (text 1 thru 4 of fromISO) as integer
    set month of fromDate to (text 6 thru 7 of fromISO) as integer
    set day of fromDate to (text 9 thru 10 of fromISO) as integer
    set hours of fromDate to 0
    set minutes of fromDate to 0
    set seconds of fromDate to 0

    set toDate to current date
    set year of toDate to (text 1 thru 4 of toISO) as integer
    set month of toDate to (text 6 thru 7 of toISO) as integer
    set day of toDate to (text 9 thru 10 of toISO) as integer
    set hours of toDate to 23
    set minutes of toDate to 59
    set seconds of toDate to 59

    tell application "Calendar"
        set allEvents to {}
        if calName is "" then
            repeat with c in calendars
                try
                    set allEvents to allEvents & (every event of c whose start date ≥ fromDate and start date ≤ toDate)
                end try
            end repeat
        else
            set allEvents to every event of calendar calName whose start date ≥ fromDate and start date ≤ toDate
        end if

        set output to ""
        repeat with e in allEvents
            set eSummary to summary of e
            set eStart to start date of e as string
            set eEnd to end date of e as string
            set eAllDay to allday event of e
            try
                set eDesc to description of e
            on error
                set eDesc to ""
            end try
            try
                set eUrl to url of e
            on error
                set eUrl to ""
            end try
            try
                set eLoc to location of e
            on error
                set eLoc to ""
            end try
            if eAllDay then
                set dayFlag to "all-day"
            else
                set dayFlag to "timed"
            end if
            set output to output & eSummary & " | " & eStart & " | " & eEnd & " | " & dayFlag & " | " & eLoc & " | " & eUrl & linefeed
        end repeat
        if output is "" then
            return "No events found"
        end if
        return output
    end tell
end run
APPLESCRIPT
    )
    echo "$result"
    log_action "list-events" "${calendar:-all}" "$from_date..$to_date"
    ;;

  create-event)
    # Read JSON from stdin (avoids exposing sensitive data in process list)
    json=$(cat)

    # Validate, normalize, and extract all fields in a single Python call.
    # Outputs one field per line for safe parsing.
    # JSON is passed via environment variable (not pipe) because the heredoc
    # already occupies stdin — a pipe would be silently discarded by bash.
    validated=$(CALENDAR_JSON="$json" python3 << 'PYEOF'
import os, sys, json

try:
    data = json.loads(os.environ['CALENDAR_JSON'])
except json.JSONDecodeError as e:
    print(f"Error: invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)

if 'summary' not in data:
    print("Error: 'summary' field is required", file=sys.stderr)
    sys.exit(1)

try:
    summary = str(data['summary'])
    calendar = str(data.get('calendar', ''))
    description = str(data.get('description', ''))
    location = str(data.get('location', ''))
    url = str(data.get('url', ''))
    recurrence = str(data.get('recurrence', ''))
    iso_date = str(data.get('iso_date', ''))
    iso_end_date = str(data.get('iso_end_date', ''))
    offset_days = int(data.get('offset_days', 0))
    hour = int(data.get('hour', 9))
    minute = int(data.get('minute', 0))
    duration_min = int(data.get('duration_minutes', 30))
    alarm_min = int(data.get('alarm_minutes', 0))
    all_day = bool(data.get('all_day', False))
except (ValueError, TypeError) as e:
    print(f"Error: invalid field value: {e}", file=sys.stderr)
    sys.exit(1)

# Range checks
errors = []
if not 0 <= hour <= 23: errors.append("hour must be 0-23")
if not 0 <= minute <= 59: errors.append("minute must be 0-59")
if duration_min < 0: errors.append("duration_minutes must be >= 0")
if alarm_min < 0: errors.append("alarm_minutes must be >= 0")

# Validate and normalize date fields
for name, val in [('iso_date', iso_date), ('iso_end_date', iso_end_date)]:
    if val:
        parts = val.split('-')
        if len(parts) != 3:
            errors.append(f"{name} must be YYYY-MM-DD")
        else:
            try:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                if not (1 <= m <= 12 and 1 <= d <= 31 and y >= 1):
                    errors.append(f"{name} has invalid date values")
                else:
                    normalized = f"{y:04d}-{m:02d}-{d:02d}"
                    if name == 'iso_date':
                        iso_date = normalized
                    else:
                        iso_end_date = normalized
            except ValueError:
                errors.append(f"{name} must contain numeric values")

if iso_end_date and not all_day:
    errors.append("iso_end_date is only valid for all-day events (set all_day: true)")

if errors:
    for e in errors:
        print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

# Safe output: replace newlines in string values (one field per line)
def safe(s):
    return s.replace('\n', ' ').replace('\r', '')

fields = [
    safe(summary), safe(calendar), safe(description), safe(location),
    safe(url), safe(recurrence), safe(iso_date), safe(iso_end_date),
    str(offset_days), str(hour), str(minute), str(duration_min), str(alarm_min),
    'true' if all_day else 'false'
]
for f in fields:
    print(f)
PYEOF
    )

    # Read validated values (one field per line, handles empty fields correctly)
    {
      read -r summary
      read -r calendar
      read -r description
      read -r location
      read -r url
      read -r recurrence
      read -r iso_date
      read -r iso_end_date
      read -r offset_days
      read -r hour
      read -r minute
      read -r duration_min
      read -r alarm_min
      read -r all_day
    } <<< "$validated"

    # Defense-in-depth: verify numeric fields are pure integers
    for var in offset_days hour minute duration_min alarm_min; do
        if ! [[ "${!var}" =~ ^-?[0-9]+$ ]]; then
            echo "Error: $var must be an integer" >&2
            exit 1
        fi
    done

    # Auto-detect calendar if not specified
    if [ -z "$calendar" ]; then
        calendar=$(osascript -e 'tell application "Calendar" to get name of first calendar')
    fi

    # Execute via osascript with argv parameter passing.
    # All user-provided strings are passed as typed parameters via "on run argv",
    # never interpolated into executable AppleScript code. This prevents injection.
    result=$(osascript - "$summary" "$description" "$calendar" "$recurrence" \
        "$offset_days" "$hour" "$minute" "$duration_min" "$alarm_min" \
        "$all_day" "$iso_date" "$location" "$url" "$iso_end_date" <<'APPLESCRIPT'
on run argv
    set evtSummary to item 1 of argv
    set evtDescription to item 2 of argv
    set calName to item 3 of argv
    set evtRecurrence to item 4 of argv
    set offsetDays to (item 5 of argv) as integer
    set evtHour to (item 6 of argv) as integer
    set evtMinute to (item 7 of argv) as integer
    set durationMin to (item 8 of argv) as integer
    set alarmMin to (item 9 of argv) as integer
    set isAllDay to (item 10 of argv) is "true"
    set isoDate to item 11 of argv
    set evtLocation to item 12 of argv
    set evtUrl to item 13 of argv
    set isoEndDate to item 14 of argv

    -- Calculate start date
    if isoDate is not "" then
        set startDate to current date
        set year of startDate to (text 1 thru 4 of isoDate) as integer
        set month of startDate to (text 6 thru 7 of isoDate) as integer
        set day of startDate to (text 9 thru 10 of isoDate) as integer
        set hours of startDate to evtHour
        set minutes of startDate to evtMinute
        set seconds of startDate to 0
    else
        set startDate to (current date) + offsetDays * days
        set hours of startDate to evtHour
        set minutes of startDate to evtMinute
        set seconds of startDate to 0
    end if

    -- Calculate end date
    if isAllDay then
        if isoEndDate is not "" then
            -- Multi-day all-day event: end = day after iso_end_date
            set endDate to current date
            set year of endDate to (text 1 thru 4 of isoEndDate) as integer
            set month of endDate to (text 6 thru 7 of isoEndDate) as integer
            set day of endDate to (text 9 thru 10 of isoEndDate) as integer
            set hours of endDate to 0
            set minutes of endDate to 0
            set seconds of endDate to 0
            set endDate to endDate + (1 * days)
        else
            -- Single all-day event: end = start + 1 day
            set endDate to startDate + (1 * days)
        end if
    else
        set endDate to startDate + durationMin * minutes
    end if

    -- Create event
    tell application "Calendar"
        -- SR-001: Reject read-only calendars
        if not (writable of calendar calName) then
            error "Calendar '" & calName & "' is read-only. Choose a writable calendar."
        end if
        tell calendar calName
            if isAllDay then
                if evtLocation is not "" then
                    set newEvent to make new event with properties {summary:evtSummary, start date:startDate, end date:endDate, allday event:true, description:evtDescription, location:evtLocation}
                else
                    set newEvent to make new event with properties {summary:evtSummary, start date:startDate, end date:endDate, allday event:true, description:evtDescription}
                end if
            else
                if evtLocation is not "" then
                    set newEvent to make new event with properties {summary:evtSummary, start date:startDate, end date:endDate, description:evtDescription, location:evtLocation}
                else
                    set newEvent to make new event with properties {summary:evtSummary, start date:startDate, end date:endDate, description:evtDescription}
                end if
            end if

            -- Set URL if provided
            if evtUrl is not "" then
                set url of newEvent to evtUrl
            end if

            -- Set recurrence if provided
            if evtRecurrence is not "" then
                set recurrence of newEvent to evtRecurrence
            end if

            -- Set alarm if provided
            if alarmMin > 0 then
                make new display alarm at end of newEvent with properties {trigger interval:-alarmMin}
            end if
        end tell
    end tell

    return "Event created: " & evtSummary
end run
APPLESCRIPT
    )
    log_action "create-event" "$calendar" "$summary"
    echo "$result"
    ;;

  batch-create)
    json=$(cat)

    # Validate array and emit one JSON object per line
    events=$(CALENDAR_JSON="$json" python3 << 'PYEOF'
import os, sys, json

try:
    data = json.loads(os.environ['CALENDAR_JSON'])
except json.JSONDecodeError as e:
    print(f"Error: invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)

if not isinstance(data, list):
    print("Error: expected JSON array", file=sys.stderr)
    sys.exit(1)

if len(data) == 0:
    print("Error: empty array", file=sys.stderr)
    sys.exit(1)

for item in data:
    if not isinstance(item, dict):
        print("Error: array items must be objects", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(item, ensure_ascii=False))
PYEOF
    )

    count=0
    errors=0
    total=$(echo "$events" | wc -l | tr -d ' ')

    while IFS= read -r event_json; do
        if result=$(echo "$event_json" | "$0" create-event 2>&1); then
            echo "$result"
            count=$((count + 1))
        else
            errors=$((errors + 1))
            echo "Error: $result" >&2
        fi
    done <<< "$events"

    echo "Batch complete: $count/$total created ($errors errors)"
    log_action "batch-create" "-" "$count/$total"
    ;;

  update-event)
    json=$(cat)

    validated=$(CALENDAR_JSON="$json" python3 << 'PYEOF'
import os, sys, json

SKIP = '__SKIP__'

try:
    data = json.loads(os.environ['CALENDAR_JSON'])
except json.JSONDecodeError as e:
    print(f"Error: invalid JSON: {e}", file=sys.stderr)
    sys.exit(1)

calendar = str(data.get('calendar', ''))
find_summary = str(data.get('find_summary', ''))
find_date = str(data.get('find_date', ''))

if not find_summary:
    print("Error: 'find_summary' is required to locate the event", file=sys.stderr)
    sys.exit(1)

if not find_date:
    print("Error: 'find_date' (YYYY-MM-DD) is required to locate the event", file=sys.stderr)
    sys.exit(1)

# Validate find_date
parts = find_date.split('-')
if len(parts) != 3:
    print("Error: find_date must be YYYY-MM-DD", file=sys.stderr)
    sys.exit(1)
try:
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    if not (1 <= m <= 12 and 1 <= d <= 31 and y >= 1):
        print("Error: find_date has invalid date values", file=sys.stderr)
        sys.exit(1)
    find_date = f"{y:04d}-{m:02d}-{d:02d}"
except ValueError:
    print("Error: find_date must contain numeric values", file=sys.stderr)
    sys.exit(1)

# Fields to update (SKIP = don't touch)
new_summary = str(data['new_summary']) if 'new_summary' in data else SKIP
new_description = str(data['description']) if 'description' in data else SKIP
new_url = str(data['url']) if 'url' in data else SKIP
new_location = str(data['location']) if 'location' in data else SKIP

def safe(s):
    return s.replace('\n', ' ').replace('\r', '')

print(safe(calendar))
print(safe(find_summary))
print(find_date)
print(safe(new_summary))
print(safe(new_description))
print(safe(new_url))
print(safe(new_location))
PYEOF
    )

    {
      read -r calendar
      read -r find_summary
      read -r find_date
      read -r new_summary
      read -r new_description
      read -r new_url
      read -r new_location
    } <<< "$validated"

    if [ -z "$calendar" ]; then
        calendar="__ALL__"
    fi

    result=$(osascript - "$calendar" "$find_summary" "$find_date" \
        "$new_summary" "$new_description" "$new_url" "$new_location" <<'APPLESCRIPT'
on run argv
    set calName to item 1 of argv
    set findSummary to item 2 of argv
    set findISO to item 3 of argv
    set newSummary to item 4 of argv
    set newDescription to item 5 of argv
    set newUrl to item 6 of argv
    set newLocation to item 7 of argv

    set findDate to current date
    set year of findDate to (text 1 thru 4 of findISO) as integer
    set month of findDate to (text 6 thru 7 of findISO) as integer
    set day of findDate to (text 9 thru 10 of findISO) as integer
    set hours of findDate to 0
    set minutes of findDate to 0
    set seconds of findDate to 0
    set nextDay to findDate + (1 * days)

    tell application "Calendar"
        set matchingEvents to {}
        if calName is "__ALL__" then
            repeat with c in calendars
                try
                    set matchingEvents to matchingEvents & (every event of c whose summary is findSummary and start date ≥ findDate and start date < nextDay)
                end try
            end repeat
        else
            tell calendar calName
                set matchingEvents to (every event whose summary is findSummary and start date ≥ findDate and start date < nextDay)
            end tell
        end if

        if (count of matchingEvents) = 0 then
            error "No event found matching '" & findSummary & "' on " & findISO
        end if
        set targetEvent to item 1 of matchingEvents

        if newSummary is not "__SKIP__" then
            set summary of targetEvent to newSummary
        end if
        if newDescription is not "__SKIP__" then
            set description of targetEvent to newDescription
        end if
        if newUrl is not "__SKIP__" then
            set url of targetEvent to newUrl
        end if
        if newLocation is not "__SKIP__" then
            set location of targetEvent to newLocation
        end if
    end tell

    return "Event updated: " & findSummary
end run
APPLESCRIPT
    )
    log_action "update-event" "$calendar" "$find_summary"
    echo "$result"
    ;;

  help|*)
    echo "macOS Calendar CLI (with location support)"
    echo ""
    echo "Commands:"
    echo "  list-calendars              List all calendars"
    echo "  list-events                 List events in date range (reads stdin JSON)"
    echo "  create-event                Create event from JSON (reads stdin)"
    echo "  batch-create                Create multiple events from JSON array (reads stdin)"
    echo "  update-event                Update existing event (reads stdin JSON)"
    echo ""
    echo "Usage:"
    echo "  echo '<json>' | calendar.sh create-event"
    echo "  echo '[<json>, ...]' | calendar.sh batch-create"
    echo ""
    echo "Run with a specific command for detailed field documentation."
    ;;
esac
