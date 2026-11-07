import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "events.json"
OUTPUT = ROOT / "recruitment.ics"
TZ = timezone(timedelta(hours=8))

def escape(value):
    return (str(value).replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;"))

def fold(line):
    chunks = []
    current = ""
    for char in line:
        if len((current + char).encode("utf-8")) > 75:
            chunks.append(current)
            current = " " + char
        else:
            current += char
    chunks.append(current)
    return "\r\n".join(chunks)

def main():
    events = json.loads(DATA.read_text(encoding="utf-8"))["events"]
    now = datetime.now(timezone.utc)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Shenyang Job Calendar//CN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:沈阳招聘会",
        "X-WR-TIMEZONE:Asia/Shanghai"
    ]
    seen = set()
    for event in events:
        required = ["id", "title", "start", "end", "location",
                    "organizer", "source_url", "verified_on", "status"]
        if any(not event.get(k) for k in required):
            raise ValueError("Missing required event fields")
        uid = event["id"]
        if uid in seen:
            raise ValueError("Duplicate event ID")
        seen.add(uid)
        url = event["source_url"]
        host = (urlparse(url).hostname or "").lower()
        if urlparse(url).scheme != "https" or not (
            host.endswith(".edu.cn") or host == "edu.cn" or
            host.endswith(".gov.cn") or host == "gov.cn"
        ):
            raise ValueError("Source must be an official HTTPS education or government site")
        if event["status"] != "confirmed":
            continue
        start = datetime.fromisoformat(event["start"])
        end = datetime.fromisoformat(event["end"])
        if start.tzinfo or end.tzinfo or end <= start:
            raise ValueError("Invalid event times")
        if end.date() < now.astimezone(TZ).date():
            continue
        description = (
            "主办方：" + event["organizer"] +
            "\n核验日期：" + event["verified_on"] +
            "\n公告：" + url
        )
        if event.get("notes"):
            description += "\n备注：" + event["notes"]
        lines.extend([
            "BEGIN:VEVENT",
            "UID:" + uid + "@shenyang-job-calendar",
            "DTSTAMP:" + now.strftime("%Y%m%dT%H%M%SZ"),
            "DTSTART:" + start.replace(tzinfo=TZ).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "DTEND:" + end.replace(tzinfo=TZ).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "SUMMARY:" + escape(event["title"]),
            "LOCATION:" + escape(event["location"]),
            "DESCRIPTION:" + escape(description),
            "URL:" + url,
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    OUTPUT.write_bytes(
        ("\r\n".join(fold(x) for x in lines) + "\r\n").encode("utf-8")
    )
    print("Calendar generated")

if __name__ == "__main__":
    main()
