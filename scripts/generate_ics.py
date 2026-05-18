#!/usr/bin/env python3
"""Generate an Apple Calendar compatible .ics file from data/festivals.csv.

No third-party packages are required.
"""
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "festivals.csv"
OUT_PATH = ROOT / "docs" / "festival_extra.ics"

CALENDAR_NAME = "节日补充｜Festivals"
CALENDAR_DESC = "只包含补充节日；不包含节气、调休、补班。"
PROD_ID = "-//Carl Wang//Festival Supplement Calendar//CN"
UID_DOMAIN = "festival-calendar"
DTSTAMP = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

REQUIRED_COLUMNS = {"enabled", "id", "name", "date", "repeat", "rrule", "category", "note"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TRUE_VALUES = {"true", "yes", "1", "y", "on", "是", "启用"}
FALSE_VALUES = {"false", "no", "0", "n", "off", "否", "停用", ""}


@dataclass(frozen=True)
class Event:
    event_id: str
    name: str
    date: str
    repeat: str
    rrule: str
    category: str
    note: str


def escape_ics_text(value: str) -> str:
    """Escape text according to RFC 5545 basics."""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold_line(line: str, limit: int = 75) -> str:
    """Fold an iCalendar line by bytes, keeping UTF-8 characters intact."""
    encoded = line.encode("utf-8")
    if len(encoded) <= limit:
        return line

    parts: list[str] = []
    current = ""
    current_len = 0
    for ch in line:
        ch_len = len(ch.encode("utf-8"))
        if current_len + ch_len > limit:
            parts.append(current)
            current = " " + ch
            current_len = 1 + ch_len
        else:
            current += ch
            current_len += ch_len
    if current:
        parts.append(current)
    return "\r\n".join(parts)


def add_days(date_str: str, days: int) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)
    return dt.strftime("%Y%m%d")


def compact_date(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")


def parse_bool(value: str, row_num: int) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"第 {row_num} 行 enabled 必须是 TRUE/FALSE，当前值：{value!r}")


def validate_id(value: str, row_num: int) -> str:
    event_id = value.strip()
    if not event_id:
        raise ValueError(f"第 {row_num} 行 id 不能为空")
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", event_id):
        raise ValueError(f"第 {row_num} 行 id 只能使用英文、数字、下划线、连字符：{event_id!r}")
    return event_id


def read_events() -> list[Event]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"找不到 CSV 文件：{CSV_PATH}")

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV 文件没有表头")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV 缺少这些列：{', '.join(sorted(missing))}")

        events: list[Event] = []
        used_ids: set[str] = set()

        for i, row in enumerate(reader, start=2):
            if not parse_bool(row.get("enabled", ""), i):
                continue

            event_id = validate_id(row.get("id", ""), i)
            if event_id in used_ids:
                raise ValueError(f"第 {i} 行 id 重复：{event_id}")
            used_ids.add(event_id)

            name = (row.get("name") or "").strip()
            if not name:
                raise ValueError(f"第 {i} 行 name 不能为空")

            date = (row.get("date") or "").strip()
            if not DATE_RE.match(date):
                raise ValueError(f"第 {i} 行 date 必须是 YYYY-MM-DD：{date!r}")
            # Validate date actually exists.
            datetime.strptime(date, "%Y-%m-%d")

            repeat = (row.get("repeat") or "none").strip().lower()
            rrule = (row.get("rrule") or "").strip()
            if repeat not in {"none", "yearly", "rrule"}:
                raise ValueError(f"第 {i} 行 repeat 只能是 none/yearly/rrule：{repeat!r}")
            if repeat == "rrule" and not rrule:
                raise ValueError(f"第 {i} 行 repeat=rrule 时 rrule 不能为空")
            if repeat != "rrule" and rrule:
                raise ValueError(f"第 {i} 行只有 repeat=rrule 时才填写 rrule")

            events.append(
                Event(
                    event_id=event_id,
                    name=name,
                    date=date,
                    repeat=repeat,
                    rrule=rrule,
                    category=(row.get("category") or "").strip(),
                    note=(row.get("note") or "").strip(),
                )
            )

    return sorted(events, key=lambda e: (e.date, e.name, e.event_id))


def event_to_ics(event: Event) -> list[str]:
    date_start = compact_date(event.date)
    date_end = add_days(event.date, 1)
    description_parts = []
    if event.category:
        description_parts.append(f"Category: {event.category}")
    if event.note:
        description_parts.append(event.note)
    description = "\n".join(description_parts)

    lines = [
        "BEGIN:VEVENT",
        f"UID:{event.event_id}@{UID_DOMAIN}",
        f"DTSTAMP:{DTSTAMP}",
        f"DTSTART;VALUE=DATE:{date_start}",
        f"DTEND;VALUE=DATE:{date_end}",
        f"SUMMARY:{escape_ics_text(event.name)}",
        "TRANSP:TRANSPARENT",
    ]
    if description:
        lines.append(f"DESCRIPTION:{escape_ics_text(description)}")

    if event.repeat == "yearly":
        lines.append("RRULE:FREQ=YEARLY")
    elif event.repeat == "rrule":
        lines.append(f"RRULE:{event.rrule}")

    lines.append("END:VEVENT")
    return lines


def generate_ics(events: list[Event]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PROD_ID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(CALENDAR_NAME)}",
        f"X-WR-CALDESC:{escape_ics_text(CALENDAR_DESC)}",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    for event in events:
        lines.extend(event_to_ics(event))
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_line(line) for line in lines) + "\r\n"


def main() -> int:
    try:
        events = read_events()
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUT_PATH.write_text(generate_ics(events), encoding="utf-8", newline="")
        print(f"Generated {OUT_PATH} with {len(events)} events.")
        return 0
    except Exception as exc:  # noqa: BLE001 - show clear CLI error
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
