import tweepy
from config import X_BEARER_TOKEN, X_SEARCH_QUERIES, X_MAX_RESULTS_PER_QUERY, SEEN_FILE
import json


def _load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


def fetch_x_posts():
    """Fetch recent AI-related posts from X using the search API."""
    if not X_BEARER_TOKEN:
        print("[X] No bearer token configured, skipping X source")
        return []

    seen = _load_seen()
    stories = []

    try:
        client = tweepy.Client(bearer_token=X_BEARER_TOKEN, wait_on_rate_limit=True)
    except Exception as e:
        print(f"[X] Failed to create client: {e}")
        return []

    for query in X_SEARCH_QUERIES:
        try:
            response = client.search_recent_tweets(
                query=query,
                max_results=min(X_MAX_RESULTS_PER_QUERY, 100),
                tweet_fields=["created_at", "public_metrics", "author_id", "text"],
                user_fields=["username", "name"],
                expansions=["author_id"],
            )

            if not response.data:
                continue

            # Build user lookup
            users = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    users[user.id] = {"username": user.username, "name": user.name}

            for tweet in response.data:
                url = f"https://x.com/i/status/{tweet.id}"
                if url in seen:
                    continue

                metrics = tweet.public_metrics or {}
                engagement = (
                    metrics.get("like_count", 0)
                    + metrics.get("retweet_count", 0) * 2
                    + metrics.get("reply_count", 0)
                )

                # Only keep tweets with some engagement
                if engagement < 10:
                    continue

                author = users.get(tweet.author_id, {})
                author_name = author.get("name", "Unknown")
                author_handle = author.get("username", "unknown")

                stories.append({
                    "title": f"@{author_handle}: {tweet.text[:80]}...",
                    "url": url,
                    "source": f"X (@{author_handle})",
                    "summary": tweet.text,
                    "published": tweet.created_at.isoformat() if tweet.created_at else "",
                    "engagement": engagement,
                    "author": author_name,
                    "type": "x_post",
                })

        except Exception as e:
            print(f"[X] Search failed for query: {e}")

    # Sort by engagement
    stories.sort(key=lambda s: s.get("engagement", 0), reverse=True)
    return stories[:15]
