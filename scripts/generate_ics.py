import csv
import os
import re
from datetime import datetime, timezone

CSV_PATH = "data/festivals.csv"
OUTPUT_PATH = "docs/festival_extra.ics"
CALENDAR_NAME = "节日补充 Festival Extra"


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


def build_event(row, row_number):
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

    dtstart = normalize_date(date, row_number, event_id)

    description_parts = []
    if category:
        description_parts.append(f"Category: {category}")
    if note:
        description_parts.append(note)
    if source_url:
        description_parts.append(f"Source: {source_url}")

    description = "\\n".join(description_parts)

    lines = [
        "BEGIN:VEVENT",
        f"UID:{escape_ics_text(event_id)}@festival-calendar",
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


def main():
    rows = read_rows()

    calendar_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WQXYUHUAI//Festival Supplement Calendar//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(CALENDAR_NAME)}",
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    event_count = 0

    for index, row in enumerate(rows, start=2):
        event = build_event(row, index)
        if event:
            calendar_lines.extend(event)
            event_count += 1

    calendar_lines.append("END:VCALENDAR")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(calendar_lines) + "\n")

    print(f"Generated {OUTPUT_PATH} with {event_count} enabled events.")


if __name__ == "__main__":
    main()
