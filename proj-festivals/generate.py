import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path

CSV_PATH = Path(__file__).with_name("festivals.csv")
OUTPUT_PATH = Path(__file__).with_name("festival_extra.ics")
CALENDAR_NAME = "Festival Supplement for iOS Calendar"
ZH_OUTPUT_PATH = Path(__file__).with_name("festival_zh.ics")
ZH_CALENDAR_NAME = "节日补充日历（纯中文）"


def escape_ics_text(value: str) -> str:
    if value is None:
        return ""
    value = str(value)
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def normalize_bool(value: str) -> bool:
    return str(value).strip().lower() in ["true", "1", "yes", "y", "on"]


def chinese_summary(value: str) -> str:
    """Remove the English suffix from a bilingual event title."""
    match = re.search(r"\s+[A-Za-z]", value)
    if match:
        value = value[:match.start()]
    return value.strip()


def chinese_description(value: str) -> str:
    return value.replace("Apple", "苹果").replace("ESG", "环境、社会及治理")


def normalize_date(value: str, row_number: int, event_id: str) -> str:
    raw = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y%m%d")
        except ValueError:
            pass

    raise ValueError(
        f"Invalid date at row {row_number}, id={event_id}: {raw}. "
        "Use YYYY-MM-DD, for example 2026-04-22."
    )


def read_rows():
    # utf-8-sig 可以兼容 Excel 友好的 CSV BOM
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(f, dialect=dialect)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV is empty.")

    required_fields = ["enabled", "id", "name", "date", "repeat"]
    fieldnames = reader.fieldnames or []

    missing = [field for field in required_fields if field not in fieldnames]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Current columns are: {fieldnames}. "
            "Make sure the first row is: enabled,id,name,date,repeat,rrule,category,note,source_url"
        )

    return rows


def build_event(row, row_number, chinese_only=False):
    enabled = normalize_bool(row.get("enabled", ""))
    if not enabled:
        return None

    event_id = str(row.get("id", "")).strip()
    name = str(row.get("name", "")).strip()
    date = str(row.get("date", "")).strip()
    repeat = str(row.get("repeat", "")).strip().lower()
    rrule = str(row.get("rrule", "")).strip()
    category = str(row.get("category", "")).strip()
    note = str(row.get("note", "")).strip()
    source_url = str(row.get("source_url", "")).strip()

    if not event_id:
        raise ValueError(f"Missing id at row {row_number}.")
    if not name:
        raise ValueError(f"Missing name at row {row_number}.")
    if not date:
        raise ValueError(f"Missing date at row {row_number}, id={event_id}.")

    if chinese_only:
        name = chinese_summary(name)
        note = chinese_description(note)

    dtstart = normalize_date(date, row_number, event_id)
    uid_domain = "festival-calendar-zh" if chinese_only else "festival-calendar"

    description_parts = []

    # Only show the user-facing note in iOS Calendar.
    # Keep category and source_url in CSV for maintenance, but do not display them in event notes.
    if note:
        description_parts.append(note)

    description = "\n".join(description_parts)
    

    lines = [
        "BEGIN:VEVENT",
        f"UID:{escape_ics_text(event_id)}@{uid_domain}",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{dtstart}",
        f"SUMMARY:{escape_ics_text(name)}",
        "TRANSP:TRANSPARENT",
    ]

    if description:
        lines.append(f"DESCRIPTION:{escape_ics_text(description)}")

    if repeat == "yearly":
        lines.append("RRULE:FREQ=YEARLY")
    elif repeat == "rrule":
        if not rrule:
            raise ValueError(f"repeat=rrule but rrule is empty at row {row_number}, id={event_id}.")
        lines.append(f"RRULE:{rrule}")
    elif repeat in ["none", "", "once"]:
        pass
    else:
        raise ValueError(
            f"Invalid repeat value at row {row_number}, id={event_id}: {repeat}. "
            "Use yearly, none, or rrule."
        )

    lines.append("END:VEVENT")
    return lines


def render_calendar(rows, calendar_name, chinese_only=False):
    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WQXYUHUAI//Festival Supplement Calendar//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name)}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0

    for index, row in enumerate(rows, start=2):
        event = build_event(row, index, chinese_only=chinese_only)
        if event:
            calendar_lines.extend(event)
            event_count += 1

    calendar_lines.append("END:VCALENDAR")
    return "\n".join(calendar_lines) + "\n", event_count


def write_calendar(output_path, output, event_count):
    # Preserve published bytes when only the build timestamp would change.
    if output_path.exists():
        previous = output_path.read_text(encoding="utf-8")
        without_stamps = lambda text: re.sub(r"^DTSTAMP:.*\n", "", text, flags=re.MULTILINE)
        if without_stamps(previous) == without_stamps(output):
            print(f"{output_path.name} unchanged; keeping the published calendar.")
            return

    os.makedirs(output_path.parent, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(output)

    print(f"Generated {output_path} with {event_count} enabled events.")


def main():
    rows = read_rows()

    for output_path, calendar_name, chinese_only in (
        (OUTPUT_PATH, CALENDAR_NAME, False),
        (ZH_OUTPUT_PATH, ZH_CALENDAR_NAME, True),
    ):
        output, event_count = render_calendar(rows, calendar_name, chinese_only=chinese_only)
        write_calendar(output_path, output, event_count)


if __name__ == "__main__":
    main()
