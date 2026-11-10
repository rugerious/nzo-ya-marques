#!/usr/bin/env python3
"""Build the public daily briefing from RSS/Atom feeds.

Standard library only. Reads briefing/feeds.json, prints briefing.json to stdout.
Only titles, links, source names and dates are kept: never article text.

    python3 briefing/build.py > briefing.json     # fetch and build
    python3 briefing/build.py --check             # validate the config, no network

Exits non-zero when nothing could be collected, so a bad morning never
overwrites the last good briefing.
"""

import datetime as dt
import email.utils
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CONFIG = pathlib.Path(__file__).with_name("feeds.json")
USER_AGENT = "nzoyamarques-briefing/1.0 (+https://nzoyamarques.com)"
MAX_BYTES = 3_000_000
TIMEOUT = 20
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def log(msg):
    print(msg, file=sys.stderr)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("feed larger than %d bytes" % MAX_BYTES)
    return data


def clean_text(text, limit=180):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def clean_link(url):
    url = (url or "").strip()
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if not k.lower().startswith("utm_")]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def find_image(node):
    """The article's thumbnail as the feed declares it (https only), or None.

    Looks at media:thumbnail, media:content, enclosure and a plain <image>.
    The page shows it from the publisher's own server; we never copy it.
    """
    candidates = []
    for el in node.iter():
        tag = el.tag.split("}")[-1]
        url = el.get("url") or el.get("href")
        if tag == "thumbnail" and url:
            candidates.append((0, url))
        elif tag in ("content", "enclosure", "link") and url:
            kind = (el.get("type") or el.get("medium") or "").lower()
            rel = (el.get("rel") or "").lower()
            if tag == "link" and rel != "enclosure":
                continue
            if kind.startswith("image") or url.lower().split("?")[0].endswith(IMAGE_EXT):
                candidates.append((1, url))
        elif tag == "image" and (el.text or "").strip().startswith("https://"):
            candidates.append((2, el.text.strip()))
    for _, url in sorted(candidates, key=lambda c: c[0]):
        url = clean_link(url)
        if url and url.startswith("https://"):
            return url
    return None


def parse_date(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        d = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def parse_feed(data):
    root = ET.fromstring(data)
    entries = []
    for item in root.iter("item"):  # RSS 2.0
        entries.append({
            "title": item.findtext("title"),
            "link": item.findtext("link"),
            "date": item.findtext("pubDate") or item.findtext("dc:date", namespaces=NS),
            "image": find_image(item),
        })
    for entry in root.iter("{%s}entry" % NS["atom"]):  # Atom
        link = entry.find("atom:link[@rel='alternate']", NS)
        if link is None:
            link = entry.find("atom:link", NS)
        entries.append({
            "title": entry.findtext("atom:title", namespaces=NS),
            "link": link.get("href") if link is not None else None,
            "date": entry.findtext("atom:published", namespaces=NS) or entry.findtext("atom:updated", namespaces=NS),
            "image": find_image(entry),
        })
    return entries


def collect(feeds, max_age, status):
    """Newest items per feed, each feed sorted newest first.

    A feed may set its own "max_age_days" (slow blogs need a wider window).
    """
    now = dt.datetime.now(dt.timezone.utc)
    per_feed = []
    for feed in feeds:
        try:
            raw = parse_feed(fetch(feed["url"]))
        except Exception as exc:  # one broken feed must not stop the briefing
            log("FAIL %s: %s" % (feed["name"], exc))
            status["failed"].append(feed["name"])
            continue
        status["ok"] += 1
        window = dt.timedelta(days=feed["max_age_days"]) if "max_age_days" in feed else max_age
        items = []
        for e in raw:
            title, link, when = clean_text(e["title"]), clean_link(e["link"]), parse_date(e["date"])
            if not title or not link or (when and now - when > window):
                continue
            items.append({
                "title": title,
                "link": link,
                "source": feed["name"],
                "tag": feed.get("tag", ""),
                "official": bool(feed.get("official")),
                "published": when.isoformat() if when else None,
                "image": e.get("image"),
            })
        items.sort(key=lambda i: i["published"] or "", reverse=True)
        log("ok   %s: %d recent" % (feed["name"], len(items)))
        per_feed.append(items)
    return per_feed


def github_projects(repos, status):
    """Public facts from the GitHub API: name, description, language, last push, link.

    No commit messages or issues: only what the repo page itself shows.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:  # higher rate limit inside GitHub Actions
        headers["Authorization"] = "Bearer " + token
    projects = []
    for full_name in repos:
        url = "https://api.github.com/repos/" + urllib.parse.quote(full_name)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                repo = json.loads(resp.read(MAX_BYTES))
        except Exception as exc:
            log("FAIL github %s: %s" % (full_name, exc))
            status["failed"].append("github:" + full_name)
            continue
        if repo.get("private"):
            continue  # never publish a private repo, even if listed by mistake
        projects.append({
            "name": clean_text(repo.get("name"), 60),
            "description": clean_text(repo.get("description"), 160),
            "language": clean_text(repo.get("language"), 30),
            "pushed_at": repo.get("pushed_at"),
            "link": clean_link(repo.get("html_url")),
        })
        log("ok   github %s" % full_name)
    projects.sort(key=lambda p: p["pushed_at"] or "", reverse=True)
    return projects


def round_robin(per_feed, limit):
    """Take the newest from each feed in turn, so one busy feed cannot fill the section."""
    picked, seen = [], set()
    while len(picked) < limit and any(per_feed):
        for items in per_feed:
            while items:
                item = items.pop(0)
                if item["link"] not in seen:
                    seen.add(item["link"])
                    picked.append(item)
                    break
            if len(picked) >= limit:
                break
    return picked


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for name, section in config["sections"].items():
        assert section["items"] > 0 and section["feeds"], name
        for feed in section["feeds"]:
            assert feed.get("max_age_days", 1) > 0, feed["name"]
    assert config["highlight"], "highlight rotation is empty"
    assert all(re.fullmatch(r"[\w.-]+/[\w.-]+", r) for r in config.get("projects", [])), "projects must be owner/repo"
    if "--check" in sys.argv:
        log("config ok")
        return 0

    max_age = dt.timedelta(days=config["max_age_days"])
    status = {"ok": 0, "failed": []}
    sections = {
        name: round_robin(collect(s["feeds"], max_age, status), s["items"])
        for name, s in config["sections"].items()
    }

    today = dt.datetime.now(dt.timezone.utc).date()
    pick = config["highlight"][today.toordinal() % len(config["highlight"])]
    hl_items = round_robin(collect(pick["feeds"], dt.timedelta(days=2), status), 1)

    projects = github_projects(config.get("projects", []), status)

    total = sum(len(v) for v in sections.values()) + len(hl_items)
    if total == 0:
        log("nothing collected: not publishing")
        return 1

    print(json.dumps({
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sources_ok": status["ok"],
        "sources_failed": status["failed"],
        "sections": sections,
        "highlight": {"topic": pick["topic"], "item": hl_items[0] if hl_items else None},
        "projects": projects,
    }, ensure_ascii=False, indent=2))
    log("built: %d items, %d sources ok, %d failed" % (total, status["ok"], len(status["failed"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
