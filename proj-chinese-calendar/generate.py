import argparse
import json
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from lunar_python import Solar

ROOT = Path(__file__).resolve().parent
CHINA_TIME = timezone(timedelta(hours=8))
SOURCE_VERSION = "1.4.8"


def escape_text(value):
    return value.replace("\\", "\\\\").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def fold_line(value):
    # RFC 5545 counts UTF-8 octets, including the continuation space.
    lines, current, length = [], "", 0
    for char in value:
        size = len(char.encode("utf-8"))
        if length + size > 75:
            lines.append(current)
            current, length = " ", 1
        current += char
        length += size
    lines.append(current)
    return "\r\n".join(lines)


def day_details(day):
    lunar = Solar.fromYmd(day.year, day.month, day.day).getLunar()
    lunar_date = f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
    yi, ji = lunar.getDayYi(sect=1), lunar.getDayJi(sect=1)
    if not yi or not ji:
        raise ValueError(f"Missing almanac data for {day}")
    return {
        "date": day.isoformat(),
        "lunar_date": lunar_date,
        "ganzhi": f"{lunar.getYearInGanZhiByLiChun()}年 {lunar.getMonthInGanZhi()}月 {lunar.getDayInGanZhi()}日",
        "yi": yi,
        "ji": ji,
        "deity": lunar.getDayTianShen(),
        "day_type": lunar.getDayTianShenType() + "日",
        "luck": lunar.getDayTianShenLuck(),
    }


def description(item):
    return "\n\n".join([
        "📅 农历\n" + item["lunar_date"],
        "🗓️ 干支\n" + item["ganzhi"],
        "✅ 宜\n" + "、".join(item["yi"]),
        "❌ 忌\n" + "、".join(item["ji"]),
        "🔎 值神\n" + " · ".join(item[key] for key in ("deity", "day_type", "luck")),
    ])


def render_calendar(items, name, now):
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//WQXYUHUAI//Chinese calendar//CN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "X-WR-CALNAME:" + escape_text(name),
        "X-WR-TIMEZONE:Asia/Shanghai",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H",
    ]
    for item in items:
        day = date.fromisoformat(item["date"])
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:chinese-calendar-{day.isoformat()}@festival-calendar",
            "DTSTAMP:" + stamp,
            f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
            f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
            "SUMMARY:" + escape_text("黄历 · " + item["lunar_date"]),
            "DESCRIPTION:" + escape_text(description(item)),
            "TRANSP:TRANSPARENT", "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return ("\r\n".join(fold_line(line) for line in lines) + "\r\n").encode("utf-8")


def generate(today, now, output_dir=ROOT):
    installed = version("lunar_python")
    if installed != SOURCE_VERSION:
        raise ValueError(f"Expected lunar_python {SOURCE_VERSION}, got {installed}")
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    past, future = config["past_days"], config["future_days"]
    if type(past) is not int or type(future) is not int or not (0 <= past <= 366 and 1 <= future <= 366):
        raise ValueError("Invalid calendar window")
    items = [day_details(today + timedelta(days=offset)) for offset in range(-past, future + 1)]
    payload = render_calendar(items, config["calendar_name"], now)
    snapshot = {
        "source": "https://github.com/6tail/lunar-python", "source_version": installed,
        "generated_at": now.isoformat(), "anchor_date": today.isoformat(),
        "start_date": items[0]["date"], "end_date": items[-1]["date"], "days": items,
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Finish calculations before replacing the last successful subscription.
    temp = output_dir / "daily.ics.tmp"
    temp.write_bytes(payload)
    temp.replace(output_dir / "daily.ics")
    (output_dir / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Chinese calendar: {len(items)} days, {items[0]['date']} to {items[-1]['date']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", type=date.fromisoformat)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    now = datetime.now(CHINA_TIME)
    generate(args.today or now.date(), now, args.output_dir)
