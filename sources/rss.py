import json
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from config import RSS_FEEDS, SEEN_FILE


def _load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


def _strip_html(text):
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)


def fetch_all_feeds():
    seen = _load_seen()
    stories = []

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            resp = requests.get(feed_url, timeout=15, headers={"User-Agent": "TheDailyTensor/1.0"})
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"[RSS] Failed to fetch {source_name}: {e}")
            continue

        for entry in feed.entries[:10]:
            url = entry.get("link", "")
            if not url or url in seen:
                continue

            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                except Exception:
                    pass

            summary = _strip_html(entry.get("summary", entry.get("description", "")))
            if len(summary) > 1000:
                summary = summary[:1000] + "..."

            stories.append({
                "title": entry.get("title", "Untitled"),
                "url": url,
                "source": source_name,
                "summary": summary,
                "published": published,
                "type": "news",
            })

    # Sort by published date (newest first)
    stories.sort(key=lambda s: s.get("published", ""), reverse=True)
    return stories
