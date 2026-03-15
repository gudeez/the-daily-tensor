import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# --- Ollama ---
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3.5:latest"

# --- X/Twitter API ---
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")

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
MAX_STORIES = 12
SERVE_PORT = 8080

# --- X search queries ---
X_SEARCH_QUERIES = [
    "(AI OR LLM OR GPT OR Claude OR Gemini) (launch OR release OR announce OR breakthrough) -is:retweet lang:en",
    "(open source AI OR new model OR foundation model) -is:retweet lang:en",
]
X_MAX_RESULTS_PER_QUERY = 20
