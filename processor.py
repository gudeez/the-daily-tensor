import requests
import time
from config import OLLAMA_URL, OLLAMA_MODEL


def _generate(prompt, max_tokens=300):
    """Call Ollama generate endpoint."""
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": 4096,
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    },
                },
                timeout=120,
            )
            data = resp.json()
            return data.get("response", "").strip()
        except Exception as e:
            print(f"[Ollama] Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(3)
    return ""


def summarize(story):
    """Summarize a story in Victorian newspaper voice."""
    source_note = ""
    if story.get("type") == "x_post":
        source_note = f"This is a post from X/Twitter by {story.get('source', 'unknown')}."
    elif story.get("type") == "github":
        source_note = f"This is a GitHub repository. Stars: {story.get('stars', 'N/A')}. Language: {story.get('language', 'N/A')}."

    prompt = f"""/no_think
You are the editor of "The Daily Tensor," a newspaper from the 1880s that covers artificial intelligence news. Write a 2-3 sentence summary of this item in the voice of a Victorian-era journalist. Be informative but colorful. Do not use modern slang.

Title: {story['title']}
Summary: {story.get('summary', 'No details available.')}
Source: {story.get('source', 'Unknown')}
{source_note}

Write ONLY the summary, no preamble:"""

    return _generate(prompt, max_tokens=200)


def generate_headline(story):
    """Generate a dramatic 1880s-style headline."""
    prompt = f"""/no_think
Rewrite this headline in the style of an 1880s newspaper. Make it dramatic and punchy. Use title case. Keep it under 15 words. Do not use quotation marks.

Original: {story['title']}
Context: {story.get('summary', '')[:200]}

Write ONLY the headline, nothing else:"""

    result = _generate(prompt, max_tokens=50)
    # Clean up - remove quotes, extra whitespace
    result = result.strip('"\'').strip()
    return result if result else story["title"]


def editorialize(stories):
    """Write an editor's column summarizing the day's themes."""
    briefs = []
    for i, s in enumerate(stories[:8], 1):
        briefs.append(f"{i}. {s['title']}: {s.get('summary', '')[:150]}")
    stories_text = "\n".join(briefs)

    prompt = f"""/no_think
You are the editor-in-chief of "The Daily Tensor," an 1880s newspaper covering artificial intelligence. Write a short Editor's Column (3-4 sentences) identifying the overarching themes in today's stories. Write in a Victorian editorial voice — authoritative, slightly pompous, but genuinely excited about the progress of science.

Today's stories:
{stories_text}

Write ONLY the editorial column, no title or preamble:"""

    return _generate(prompt, max_tokens=300)


def generate_telegram_digest(stories, editorial):
    """Generate a concise Telegram-friendly digest."""
    briefs = []
    for s in stories[:8]:
        briefs.append(f"- {s['title']}: {s.get('summary', '')[:100]}")
    stories_text = "\n".join(briefs)

    prompt = f"""/no_think
You are writing a brief Telegram message digest for "The Daily Tensor" AI newsletter. Summarize the top stories in a punchy, readable format. Use emoji sparingly. Keep it under 300 words. Include the most important 5-6 stories.

Editor's take: {editorial}

Stories:
{stories_text}

Write the Telegram message:"""

    return _generate(prompt, max_tokens=400)
