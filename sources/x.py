import json
import re
from config import SEEN_FILE


def _load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


# Curated AI accounts and search terms to scrape
X_ACCOUNTS = [
    # Companies
    "AnthropicAI", "OpenAI", "GoogleDeepMind", "huggingface",
    "AIatMeta", "NVIDIAAIDev", "MistralAI", "StabilityAI",
    "GoogleAI", "CohereAI", "xaborAI",
    # People
    "sama",            # Sam Altman (OpenAI)
    "karpathy",        # Andrej Karpathy
    "ylecun",          # Yann LeCun (Meta)
    "DrJimFan",        # Jim Fan (NVIDIA)
    "AravSrinivas",    # Aravind Srinivas (Perplexity)
    "ClemDelangue",    # Clem Delangue (Hugging Face)
    "EMostaque",       # Emad Mostaque (Stability AI)
]


def _scrape_profile(account):
    """Scrape recent posts from an X profile using Scrapling."""
    from scrapling.fetchers import StealthyFetcher

    stories = []
    try:
        page = StealthyFetcher.fetch(
            f"https://x.com/{account}",
            headless=True,
            network_idle=True,
            wait=5,
        )

        # X renders tweets in article elements or divs with data-testid="tweet"
        tweets = page.css('[data-testid="tweet"]')
        if not tweets:
            # Fallback: try article tags
            tweets = page.css('article')

        for tweet in tweets[:10]:
            # Extract tweet text from spans inside tweetText
            text_el = tweet.css('[data-testid="tweetText"]')
            text = ""
            if text_el:
                spans = text_el[0].css('span')
                text = " ".join(s.text for s in spans if s.text)
            if not text or len(text) < 20:
                continue

            # Extract link to tweet via time element's parent <a>
            time_el = tweet.css('time')
            tweet_url = ""
            if time_el:
                parent = time_el[0].parent
                if parent is not None and parent.tag == 'a':
                    href = parent.attrib.get("href", "")
                    if "/status/" in href:
                        tweet_url = f"https://x.com{href}"

            if not tweet_url:
                continue

            # Extract engagement metrics from like/retweet/reply buttons
            engagement = 0
            for testid in ["like", "retweet", "reply"]:
                els = tweet.css(f'[data-testid="{testid}"]')
                for el in els:
                    spans = el.css('span')
                    for s in spans:
                        if s.text and s.text.strip():
                            engagement += _parse_count(s.text.strip())

            # Extract timestamp
            published = ""
            if time_el:
                published = time_el[0].attrib.get("datetime", "")

            stories.append({
                "title": f"@{account}: {text[:80]}...",
                "url": tweet_url,
                "source": f"X (@{account})",
                "summary": text,
                "published": published,
                "engagement": engagement,
                "author": account,
                "type": "x_post",
            })

    except Exception as e:
        print(f"[X] Failed to scrape @{account}: {e}")

    return stories


def _parse_count(text):
    """Parse engagement counts like '1.2K', '45', '3.1M'."""
    if not text:
        return 0
    text = text.strip().upper().replace(",", "")
    try:
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        elif "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        else:
            return int(re.sub(r'[^\d]', '', text) or 0)
    except (ValueError, TypeError):
        return 0


def fetch_x_posts():
    """Fetch AI-related posts from X by scraping profiles and search."""
    seen = _load_seen()
    all_stories = []

    # Scrape AI accounts
    for account in X_ACCOUNTS:
        print(f"  [X] Scraping @{account}...")
        posts = _scrape_profile(account)
        all_stories.extend(posts)

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for s in all_stories:
        if s["url"] not in seen_urls and s["url"] not in seen:
            seen_urls.add(s["url"])
            unique.append(s)

    # Sort by engagement (scraped accounts first since they have metrics)
    unique.sort(key=lambda s: s.get("engagement", 0), reverse=True)

    print(f"  [X] Total unique posts: {len(unique)}")
    return unique[:30]
