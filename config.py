import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Auto-load .env file if present
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# --- Ollama ---
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3.5:latest"

# --- Telegram (matches your other projects' env var names) ---
TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHANNEL_ID = os.environ.get("TG_CHANNEL_ID", "")  # e.g. "@your_channel" or "-100xxxxx"

# --- RSS Feeds (AI news) ---
RSS_FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "arXiv cs.AI": "https://rss.arxiv.org/rss/cs.AI",
    "MIT Tech Review AI": "https://www.technologyreview.com/feed/",
}

# --- GitHub ---
GITHUB_TOPICS = ["llm", "artificial-intelligence", "machine-learning", "generative-ai"]

# --- Output ---
EDITIONS_DIR = BASE_DIR / "editions"
DATA_DIR = BASE_DIR / "data"
SEEN_FILE = DATA_DIR / "seen.json"
MAX_STORIES = 48
SERVE_PORT = 8080

