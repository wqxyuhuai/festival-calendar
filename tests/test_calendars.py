import importlib.util
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


chinese = module("chinese", "chinese-calendar/generate.py")
festivals = module("festivals", "festivals/generate.py")
site = module("site_builder", "scripts/build_site.py")


class CalendarTests(unittest.TestCase):
    def test_screenshot_reference(self):
        item = chinese.day_details(date(2026, 8, 21))
        self.assertEqual(item["lunar_date"], "七月初九")
        self.assertEqual(item["ganzhi"], "丙午年 丙申月 丁卯日")
        self.assertEqual((item["deity"], item["day_type"], item["luck"]), ("朱雀", "黑道日", "凶"))
        self.assertEqual(set(item["yi"]), set("嫁娶 出行 解除 移徙 立券 交易 入宅 开市 祈福 栽种 安床 安葬 祭祀 安香 出火 伐木 开光 求嗣".split()))
        self.assertEqual(set(item["ji"]), set("理发 动土 作灶 掘井 开池 破土".split()))
        description = chinese.description(item)
        self.assertNotIn("来源", description)
        self.assertTrue(all(not line.startswith(" ") for line in description.splitlines()))

    def test_lunar_reference_and_term_boundary(self):
        for day, expected in [(date(2026, 2, 17), "正月初一"), (date(2026, 8, 27), "七月十五"), (date(2025, 7, 25), "闰六月初一")]:
            with self.subTest(day=day):
                self.assertEqual(chinese.day_details(day)["lunar_date"], expected)
        self.assertTrue(chinese.day_details(date(2026, 2, 3))["ganzhi"].startswith("乙巳年 己丑月"))
        self.assertTrue(chinese.day_details(date(2026, 2, 4))["ganzhi"].startswith("丙午年 庚寅月"))

    def test_rolling_window_format_and_stable_uid(self):
        now = datetime(2026, 12, 31, 12, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            chinese.generate(date(2026, 12, 31), now, target)
            data = (target / "daily.ics").read_bytes()
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
            self.assertTrue(all(len(line) <= 75 for line in data.split(b"\r\n")))
            unfolded = data.decode().replace("\r\n ", "")
            self.assertEqual(unfolded.count("BEGIN:VEVENT"), 68)
            self.assertNotIn("VALARM", unfolded)
            self.assertNotIn("RRULE", unfolded)
            snapshot = json.loads((target / "snapshot.json").read_text(encoding="utf-8"))
            days = [date.fromisoformat(item["date"]) for item in snapshot["days"]]
            self.assertEqual(days, [date(2026, 12, 24) + timedelta(days=i) for i in range(68)])
            for event in unfolded.split("BEGIN:VEVENT\r\n")[1:]:
                props = dict(line.split(":", 1) for line in event.split("\r\nEND:VEVENT")[0].split("\r\n"))
                start = datetime.strptime(props["DTSTART;VALUE=DATE"], "%Y%m%d").date()
                self.assertEqual(props["DTEND;VALUE=DATE"], (start + timedelta(days=1)).strftime("%Y%m%d"))
                self.assertEqual(props["UID"], f"chinese-calendar-{start.isoformat()}@festival-calendar")
            first_uids = {line for line in unfolded.splitlines() if line.startswith("UID:")}
            chinese.generate(date(2027, 1, 1), now + timedelta(days=1), target)
            next_uids = {line for line in (target / "daily.ics").read_text(encoding="utf-8").splitlines() if line.startswith("UID:")}
            self.assertEqual(len(first_uids & next_uids), 67)

    def test_failure_preserves_previous_subscription(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / "daily.ics").write_bytes(b"last successful file")
            with patch.object(chinese, "day_details", side_effect=ValueError("bad data")):
                with self.assertRaises(ValueError):
                    chinese.generate(date(2026, 9, 20), datetime.now(timezone.utc), target)
            self.assertEqual((target / "daily.ics").read_bytes(), b"last successful file")

    def test_festival_generation_preserves_published_bytes(self):
        original = festivals.OUTPUT_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "festival.ics"
            output.write_bytes(original)
            with patch.object(festivals, "OUTPUT_PATH", output):
                festivals.main()
            self.assertEqual(output.read_bytes(), original)

    def test_site_keeps_old_subscription_path(self):
        with tempfile.TemporaryDirectory() as temp:
            site.build_site(Path(temp))
            self.assertEqual((Path(temp) / "festival_extra.ics").read_bytes(), festivals.OUTPUT_PATH.read_bytes())
            self.assertTrue((Path(temp) / "chinese-calendar/daily.ics").is_file())
            self.assertTrue((Path(temp) / "festivals/index.html").is_file())


if __name__ == "__main__":
    unittest.main()
