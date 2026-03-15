"""
X/Twitter source using search scraping + engagement velocity scoring.

Strategy:
1. Scrape X's explore/trending page for current trends
2. Poll keyword searches for AI/crypto/privacy content
3. Score posts by engagement velocity (engagement / age^1.5)
4. Cluster similar posts via Jaccard similarity
5. Surface the top post per cluster
"""
import json
import re
import hashlib
from datetime import datetime, timezone, timedelta
from config import SEEN_FILE
from scrapling.fetchers import StealthyFetcher


# High-signal keyword queries for each vertical
KEYWORD_SETS = {
    "AI": [
        "artificial intelligence OR LLM OR generative AI",
        "new AI model OR AI launch OR AI release",
        "GPT OR Claude OR Gemini OR Llama announcement",
        "open source AI OR foundation model",
    ],
    "Crypto": [
        "crypto OR bitcoin OR ethereum OR defi",
        "solana OR base chain OR web3 launch",
        "token launch OR airdrop OR crypto regulation",
    ],
    "Privacy": [
        "data privacy OR surveillance OR encryption",
        "GDPR OR data breach OR zero knowledge",
        "end to end encryption OR privacy law",
    ],
}


def _load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


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


def _extract_posts_from_page(page):
    """Extract post data from a scrapled X page."""
    posts = []
    tweets = page.css('[data-testid="tweet"]')
    if not tweets:
        tweets = page.css('article')

    for tweet in tweets[:15]:
        # Text
        text_el = tweet.css('[data-testid="tweetText"]')
        text = ""
        if text_el:
            spans = text_el[0].css('span')
            text = " ".join(s.text for s in spans if s.text)
        if not text or len(text) < 20:
            continue

        # Author
        author = "unknown"
        author_els = tweet.css('[data-testid="User-Name"] a')
        if author_els:
            href = author_els[0].attrib.get("href", "")
            if href:
                author = href.strip("/").split("/")[0]

        # URL + timestamp
        time_el = tweet.css('time')
        tweet_url = ""
        published = ""
        if time_el:
            published = time_el[0].attrib.get("datetime", "")
            parent = time_el[0].parent
            if parent is not None and parent.tag == 'a':
                href = parent.attrib.get("href", "")
                if "/status/" in href:
                    tweet_url = f"https://x.com{href}"

        if not tweet_url:
            continue

        # Engagement metrics
        likes = 0
        retweets = 0
        replies = 0
        for testid, metric_name in [("like", "likes"), ("retweet", "retweets"), ("reply", "replies")]:
            els = tweet.css(f'[data-testid="{testid}"]')
            for el in els:
                for s in el.css('span'):
                    if s.text and s.text.strip():
                        val = _parse_count(s.text.strip())
                        if testid == "like":
                            likes = max(likes, val)
                        elif testid == "retweet":
                            retweets = max(retweets, val)
                        elif testid == "reply":
                            replies = max(replies, val)

        # Calculate velocity score
        velocity = 0
        hours_old = 1  # default
        if published:
            try:
                post_time = datetime.fromisoformat(published.replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - post_time
                hours_old = max(age.total_seconds() / 3600, 0.5)

                # Skip posts older than 30 days (velocity handles recency ranking)
                if hours_old > 720:
                    continue
            except Exception:
                pass

        raw_engagement = likes + (2 * retweets) + (3 * replies)
        velocity = raw_engagement / (hours_old ** 1.5)

        posts.append({
            "title": f"@{author}: {text[:80]}...",
            "url": tweet_url,
            "source": f"X (@{author})",
            "summary": text,
            "published": published,
            "engagement": raw_engagement,
            "velocity": velocity,
            "hours_old": round(hours_old, 1),
            "author": author,
            "type": "x_post",
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
        })

    return posts


def _scrape_trending():
    """Scrape X's trending/explore page for current trends."""
    trends = []
    try:
        print("  [X] Scraping trending topics...")
        page = StealthyFetcher.fetch(
            "https://x.com/explore/tabs/trending",
            headless=True,
            network_idle=True,
        )

        # Trending items are in spans within the explore page
        trend_items = page.css('[data-testid="trend"]')
        for item in trend_items[:20]:
            spans = item.css('span')
            trend_text = " ".join(s.text for s in spans if s.text).strip()
            if trend_text and len(trend_text) > 2:
                trends.append(trend_text)

        if not trends:
            # Fallback: look for any prominent text links
            links = page.css('a[href*="/search"]')
            for link in links[:20]:
                text = link.text.strip() if link.text else ""
                if text and len(text) > 2:
                    trends.append(text)

        print(f"  [X] Found {len(trends)} trending topics")
    except Exception as e:
        print(f"  [X] Failed to scrape trending: {e}")

    return trends


def _scrape_search(query):
    """Scrape X search results for a query (logged-out view)."""
    from urllib.parse import quote
    posts = []
    encoded = quote(query)

    cookies = _get_cookies()
    try:
        kwargs = {
            "headless": True,
            "network_idle": True,
        }
        if cookies:
            kwargs["cookies"] = cookies

        page = StealthyFetcher.fetch(
            f"https://x.com/search?q={encoded}&src=typed_query&f=top",
            **kwargs,
        )

        # Check if we got redirected to login
        current_url = ""
        try:
            current_url = page.url if hasattr(page, 'url') else ""
        except Exception:
            pass

        if "login" in str(current_url).lower():
            return posts

        posts = _extract_posts_from_page(page)
    except Exception as e:
        print(f"  [X] Search failed for '{query[:30]}': {e}")

    return posts


def _get_cookies():
    """Load X session cookies from cookies.json if available."""
    cookie_file = SEEN_FILE.parent / "x_cookies.json"
    if cookie_file.exists():
        try:
            return json.loads(cookie_file.read_text())
        except Exception:
            pass
    return None


def _scrape_profile(account):
    """Scrape recent posts from an account."""
    posts = []
    cookies = _get_cookies()
    try:
        kwargs = {
            "headless": True,
            "network_idle": True,
        }
        if cookies:
            kwargs["cookies"] = cookies

        page = StealthyFetcher.fetch(f"https://x.com/{account}", **kwargs)
        posts = _extract_posts_from_page(page)
    except Exception as e:
        print(f"  [X] Failed to scrape @{account}: {e}")
    return posts


def _tokenize(text):
    """Simple tokenization for similarity comparison."""
    return set(re.findall(r'\w+', text.lower()))


def _jaccard(a, b):
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0
    return len(a & b) / len(a | b)


def _cluster_posts(posts, threshold=0.4):
    """Cluster similar posts, keep highest-velocity post per cluster."""
    if not posts:
        return []

    # Tokenize all posts
    tokenized = [_tokenize(p["summary"]) for p in posts]

    clusters = []  # list of lists of indices
    assigned = set()

    # Sort by velocity first so cluster representatives are the best ones
    order = sorted(range(len(posts)), key=lambda i: posts[i].get("velocity", 0), reverse=True)

    for i in order:
        if i in assigned:
            continue

        cluster = [i]
        assigned.add(i)

        for j in order:
            if j in assigned:
                continue

            # Check URL-based dedup first
            if posts[i].get("url") == posts[j].get("url"):
                cluster.append(j)
                assigned.add(j)
                continue

            # Jaccard similarity on text
            sim = _jaccard(tokenized[i], tokenized[j])
            if sim >= threshold:
                cluster.append(j)
                assigned.add(j)

        clusters.append(cluster)

    # Return the top post from each cluster (already sorted by velocity)
    return [posts[c[0]] for c in clusters]


# Accounts organized by vertical — high-frequency posters
ACCOUNTS = {
    "AI": [
        "AnthropicAI", "OpenAI", "GoogleDeepMind", "huggingface",
        "MistralAI", "AIatMeta", "NVIDIAAIDev", "CohereAI",
        "karpathy", "ylecun", "DrJimFan", "AravSrinivas",
        "ClemDelangue", "sama", "GaryMarcus",
    ],
    "Crypto": [
        "VitalikButerin", "punk6529", "CoinDesk", "TheBlock__",
        "coinaboretelegraph", "brian_armstrong", "caboroYakovenko",
        "jessePollak", "ethereum", "solana",
    ],
    "Privacy": [
        "EFF", "Snowden", "signalapp", "ProtonMail",
        "torproject", "privacyint",
    ],
}


def fetch_x_posts():
    """Full pipeline: trending + keyword search + profile scraping + velocity + clustering."""
    seen = _load_seen()
    all_posts = []

    # Step 1: Try trending topics
    trends = _scrape_trending()

    # Filter trends for our verticals
    ai_keywords = {"ai", "gpt", "llm", "model", "claude", "gemini", "openai", "anthropic", "neural", "robot"}
    crypto_keywords = {"crypto", "bitcoin", "btc", "ethereum", "eth", "defi", "token", "blockchain", "solana", "web3"}
    privacy_keywords = {"privacy", "surveillance", "encrypt", "breach", "gdpr", "data"}
    all_keywords = ai_keywords | crypto_keywords | privacy_keywords

    relevant_trends = []
    for t in trends:
        t_lower = t.lower()
        if any(kw in t_lower for kw in all_keywords):
            relevant_trends.append(t)

    if relevant_trends:
        print(f"  [X] Relevant trends: {', '.join(relevant_trends[:5])}")

    # Step 2: Search keyword queries
    search_worked = False
    for vertical, queries in KEYWORD_SETS.items():
        for query in queries[:2]:  # Limit to 2 per vertical to save time
            print(f"  [X] Searching: {query[:40]}...")
            posts = _scrape_search(query)
            if posts:
                search_worked = True
                all_posts.extend(posts)
                print(f"      Found {len(posts)} posts")
            else:
                print(f"      No results (may require login)")

    # Step 3: Also search relevant trends
    for trend in relevant_trends[:3]:
        print(f"  [X] Searching trend: {trend}...")
        posts = _scrape_search(trend)
        if posts:
            all_posts.extend(posts)
            print(f"      Found {len(posts)} posts")

    # Step 4: If search didn't work (login wall), scrape accounts by vertical
    if not search_worked:
        print("  [X] Search requires login, scraping accounts by vertical...")
        for vertical, accts in ACCOUNTS.items():
            print(f"  [X] --- {vertical} ---")
            for account in accts:
                print(f"  [X] Scraping @{account}...")
                posts = _scrape_profile(account)
                all_posts.extend(posts)

    # Step 5: Deduplicate against seen
    unique = []
    seen_urls = set()
    for p in all_posts:
        if p["url"] not in seen_urls and p["url"] not in seen:
            seen_urls.add(p["url"])
            unique.append(p)

    print(f"  [X] {len(unique)} unique posts before clustering")

    # Step 6: Cluster similar posts
    clustered = _cluster_posts(unique)
    print(f"  [X] {len(clustered)} posts after clustering")

    # Step 7: Sort by velocity score
    clustered.sort(key=lambda p: p.get("velocity", 0), reverse=True)

    # Log top posts
    for p in clustered[:5]:
        print(f"      [{p['velocity']:.0f}v] @{p['author']}: {p['summary'][:60]}...")

    return clustered[:30]
