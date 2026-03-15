import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from config import GITHUB_TOPICS, SEEN_FILE
import json


def _load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return {}


def fetch_trending():
    """Scrape GitHub trending page for AI-related repos."""
    seen = _load_seen()
    stories = []

    try:
        resp = requests.get(
            "https://github.com/trending",
            timeout=15,
            headers={"User-Agent": "TheDailyTensor/1.0"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")

        for article in soup.select("article.Box-row"):
            h2 = article.select_one("h2 a")
            if not h2:
                continue

            repo_path = h2.get("href", "").strip("/")
            url = f"https://github.com/{repo_path}"

            if url in seen:
                continue

            desc_p = article.select_one("p")
            description = desc_p.get_text(strip=True) if desc_p else ""

            # Check if AI-related
            text_lower = (repo_path + " " + description).lower()
            ai_keywords = ["ai", "llm", "gpt", "model", "neural", "transformer",
                           "machine-learning", "deep-learning", "diffusion", "agent",
                           "inference", "embedding", "langchain", "rag", "fine-tun"]
            if not any(kw in text_lower for kw in ai_keywords):
                continue

            stars_el = article.select_one("[href$='/stargazers']")
            stars = stars_el.get_text(strip=True).replace(",", "") if stars_el else "0"

            lang_el = article.select_one("[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else ""

            stories.append({
                "title": repo_path,
                "url": url,
                "source": "GitHub Trending",
                "summary": description,
                "stars": stars,
                "language": language,
                "type": "github",
            })
    except Exception as e:
        print(f"[GitHub] Failed to fetch trending: {e}")

    return stories


def fetch_notable_repos():
    """Find newly popular AI repos via GitHub search API."""
    seen = _load_seen()
    stories = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")

    for topic in GITHUB_TOPICS:
        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"{topic} created:>{cutoff}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 5,
                },
                timeout=15,
                headers={"User-Agent": "TheDailyTensor/1.0"},
            )
            data = resp.json()

            for repo in data.get("items", []):
                url = repo["html_url"]
                if url in seen:
                    continue
                if repo["stargazers_count"] < 10:
                    continue

                stories.append({
                    "title": repo["full_name"],
                    "url": url,
                    "source": "GitHub New",
                    "summary": repo.get("description", "") or "",
                    "stars": str(repo["stargazers_count"]),
                    "language": repo.get("language", "") or "",
                    "type": "github",
                })
        except Exception as e:
            print(f"[GitHub] Failed search for '{topic}': {e}")

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for s in stories:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            unique.append(s)

    unique.sort(key=lambda s: int(s.get("stars", "0")), reverse=True)
    return unique[:10]
