import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_site(destination=ROOT / "_site"):
    destination = Path(destination)
    snapshot = json.loads((ROOT / "chinese-calendar/snapshot.json").read_text(encoding="utf-8"))
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    if not snapshot["start_date"] <= today <= snapshot["end_date"]:
        print("::warning::Last successful Chinese calendar does not cover today. Festival publication continues.")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "doc-festivals/index.html", destination / "index.html")
    shutil.copy2(ROOT / "festivals/festival_extra.ics", destination / "festival_extra.ics")
    for source, target in (("doc-festivals", "festivals"), ("doc-chinese-calendar", "chinese-calendar")):
        shutil.copytree(ROOT / source, destination / target, dirs_exist_ok=True)
    shutil.copy2(ROOT / "chinese-calendar/daily.ics", destination / "chinese-calendar/daily.ics")
    (destination / ".nojekyll").touch()
    print("Site assembled; original /festival_extra.ics subscription preserved.")


if __name__ == "__main__":
    build_site()
