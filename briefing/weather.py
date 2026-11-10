#!/usr/bin/env python3
"""Current weather for Manchester, Lisbon and Luanda, from Open-Meteo.

Standard library only. Prints weather.json to stdout; exits non-zero if no city
answered, so a bad hour never overwrites the last good file.

Open-Meteo free API: non-commercial use, under 10,000 calls a day, data under
CC BY 4.0 (the page credits Open-Meteo). We make 3 calls an hour.

    python3 briefing/weather.py > weather.json
    python3 briefing/weather.py --check     # no network
"""

import datetime as dt
import json
import sys
import urllib.parse
import urllib.request

CITIES = [
    {"name": "Manchester", "lat": 53.4808, "lon": -2.2426},
    {"name": "Lisbon", "lat": 38.7223, "lon": -9.1393},
    {"name": "Luanda", "lat": -8.8390, "lon": 13.2894},
]
API = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "nzoyamarques-weather/1.0 (+https://nzoyamarques.com)"

# WMO weather codes grouped into the few looks the page draws.
def kind(code):
    if code in (0, 1):
        return "clear"
    if code == 2:
        return "partly"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "snow"
    if code >= 95:
        return "storm"
    return "cloudy"


def fetch(city):
    query = urllib.parse.urlencode({
        "latitude": city["lat"],
        "longitude": city["lon"],
        "current": "temperature_2m,weather_code,is_day",
        "timezone": "auto",
    })
    req = urllib.request.Request(API + "?" + query, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read(200_000))
    cur = data["current"]
    return {
        "name": city["name"],
        "temp": round(float(cur["temperature_2m"])),
        "kind": kind(int(cur["weather_code"])),
        "day": bool(cur.get("is_day", 1)),
    }


def main():
    assert all(-90 <= c["lat"] <= 90 and -180 <= c["lon"] <= 180 for c in CITIES)
    if "--check" in sys.argv:
        print("config ok", file=sys.stderr)
        return 0
    out = []
    for city in CITIES:
        try:
            out.append(fetch(city))
            print("ok   %s" % city["name"], file=sys.stderr)
        except Exception as exc:
            print("FAIL %s: %s" % (city["name"], exc), file=sys.stderr)
    if not out:
        return 1
    print(json.dumps({
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "Open-Meteo.com (CC BY 4.0)",
        "cities": out,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
