import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Central Standard Time (UTC-6) / Central Daylight Time (UTC-5)
# Using CDT since DST is active in March
CST = timezone(timedelta(hours=-5))
from jinja2 import Environment, FileSystemLoader
from config import EDITIONS_DIR, DATA_DIR, SEEN_FILE, MAX_STORIES, BASE_DIR
from sources.rss import fetch_all_feeds
from sources.github import fetch_trending, fetch_notable_repos
from sources.x import fetch_x_posts
from processor import summarize, generate_headline, editorialize, generate_telegram_digest, get_stats, reset_stats
from telegram_bot import send_edition_to_telegram


def _load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


def _save_seen(seen):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, indent=2))


def _process_story(story):
    """Run a story through the LLM for headline + summary."""
    print(f"  Processing: {story['title'][:60]}...")
    headline = generate_headline(story)
    body = summarize(story)
    return {
        **story,
        "headline": headline,
        "body": body,
    }


def build_edition(send_telegram=True):
    """Run the full pipeline: fetch -> process -> render -> publish."""
    now = datetime.now(CST)
    date_str = now.strftime("%Y-%m-%d")
    date_fancy = now.strftime("%A, %B %d, %Y")

    # Calculate edition number (days since project start)
    start = datetime(2026, 3, 14, tzinfo=CST)
    edition_number = max(1, (now - start).days + 1)

    print(f"\n{'='*60}")
    print(f"  THE DAILY TENSOR — Edition #{edition_number}")
    print(f"  {date_fancy}")
    print(f"{'='*60}\n")

    # --- Fetch from all sources ---
    print("[1/5] Fetching RSS feeds...")
    rss_stories = fetch_all_feeds()
    print(f"  Found {len(rss_stories)} RSS stories")

    print("[2/5] Fetching X posts...")
    x_stories_raw = fetch_x_posts()
    print(f"  Found {len(x_stories_raw)} X posts")

    print("[3/5] Fetching GitHub repos...")
    gh_trending = fetch_trending()
    gh_notable = fetch_notable_repos()
    gh_stories_raw = gh_trending + gh_notable
    # Dedupe
    seen_urls = set()
    gh_stories_deduped = []
    for s in gh_stories_raw:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            gh_stories_deduped.append(s)
    print(f"  Found {len(gh_stories_deduped)} GitHub repos")

    # --- Select top stories (cap per source for variety) ---
    MAX_PER_SOURCE = 8
    source_counts = {}
    balanced_news = []
    for s in rss_stories:
        src = s["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
        if source_counts[src] <= MAX_PER_SOURCE:
            balanced_news.append(s)
    news_to_process = balanced_news[:MAX_STORIES]
    x_to_process = x_stories_raw[:20]
    gh_to_process = gh_stories_deduped[:24]

    total = len(news_to_process) + len(x_to_process) + len(gh_to_process)
    if total == 0:
        print("\nNo new stories found. Skipping edition.")
        return None

    # --- Process through LLM ---
    reset_stats()
    print(f"\n[4/5] Processing {total} stories through Qwen 3.5...")
    print(f"       ({len(news_to_process)} news + {len(x_to_process)} X + {len(gh_to_process)} GitHub) x 2 LLM calls each = ~{total * 2} calls")

    print("\n  --- News Stories ---")
    news_processed = [_process_story(s) for s in news_to_process]

    print("\n  --- X Dispatches ---")
    x_processed = [_process_story(s) for s in x_to_process]

    print("\n  --- GitHub Repos ---")
    gh_processed = [_process_story(s) for s in gh_to_process]

    all_stories = news_processed + x_processed + gh_processed
    print("\n  Writing editor's column...")
    editorial = editorialize(all_stories)

    # --- LLM stats summary ---
    stats = get_stats()
    print(f"\n  {'-'*50}")
    print(f"  LLM Stats: {stats['success']}/{stats['calls']} succeeded, {stats['failed']} failed, {stats['retries']} retries")
    print(f"  Total LLM time: {stats['total_time']:.1f}s ({stats['total_time']/60:.1f}m) | ~{stats['total_tokens']} tokens")
    if stats['success'] > 0:
        print(f"  Avg per call: {stats['total_time']/stats['success']:.1f}s")
    print(f"  {'-'*50}")

    # --- Render HTML ---
    print("\n[5/5] Rendering newspaper...")
    env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"))
    template = env.get_template("newspaper.html")

    # Find previous edition for pagination
    EDITIONS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(f.stem for f in EDITIONS_DIR.glob("2*.html"))
    prev_edition = None
    for ed in reversed(existing):
        if ed < date_str:
            prev_edition = ed
            break

    html = template.render(
        date=date_str,
        date_fancy=date_fancy,
        edition_number=edition_number,
        year=now.year,
        editorial=editorial,
        news_stories=news_processed,
        x_stories=x_processed,
        github_stories=gh_processed,
        prev_edition=prev_edition,
        next_edition=None,
    )

    # Write edition files
    edition_path = EDITIONS_DIR / f"{date_str}.html"
    latest_path = EDITIONS_DIR / "latest.html"

    edition_path.write_text(html, encoding="utf-8")
    latest_path.write_text(html, encoding="utf-8")

    # Update previous edition to link forward to this one
    if prev_edition:
        prev_path = EDITIONS_DIR / f"{prev_edition}.html"
        if prev_path.exists():
            prev_html = prev_path.read_text(encoding="utf-8")
            prev_html = prev_html.replace(
                'data-next=""', f'data-next="{date_str}"'
            )
            prev_path.write_text(prev_html, encoding="utf-8")
    print(f"  Saved: {edition_path}")
    print(f"  Saved: {latest_path}")

    # --- Update seen list ---
    seen = _load_seen()
    for s in all_stories:
        seen[s["url"]] = {"title": s["title"], "date": date_str}
    _save_seen(seen)

    # --- Telegram ---
    if send_telegram:
        print("\n  Sending Telegram digest...")
        digest = generate_telegram_digest(all_stories, editorial)
        send_edition_to_telegram(digest, date_fancy)

    print(f"\n{'='*60}")
    print(f"  Edition #{edition_number} complete!")
    print(f"  Open: file://{edition_path}")
    print(f"{'='*60}\n")

    return str(edition_path)
