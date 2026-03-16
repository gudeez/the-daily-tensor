import requests
import time
from config import OLLAMA_URL, OLLAMA_MODEL

# Track stats across the generation run
_stats = {"calls": 0, "success": 0, "failed": 0, "retries": 0, "total_time": 0.0, "total_tokens": 0}


def get_stats():
    """Return current LLM call stats."""
    return _stats.copy()


def reset_stats():
    """Reset stats for a new run."""
    _stats.update({"calls": 0, "success": 0, "failed": 0, "retries": 0, "total_time": 0.0, "total_tokens": 0})


def _generate(prompt, max_tokens=300, label="generate"):
    """Call Ollama chat endpoint with thinking disabled."""
    # Strip /no_think prefix if present (handled via API now)
    prompt = prompt.removeprefix("/no_think").strip()

    _stats["calls"] += 1
    call_num = _stats["calls"]
    prompt_len = len(prompt)
    print(f"  [LLM #{call_num}] {label} | prompt={prompt_len} chars | max_tokens={max_tokens}")

    for attempt in range(3):
        if attempt > 0:
            _stats["retries"] += 1
            print(f"  [LLM #{call_num}] Retry {attempt + 1}/3 after 3s backoff...")
        t0 = time.time()
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "think": False,
                    "options": {
                        "num_ctx": 4096,
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    },
                },
                timeout=120,
            )
            elapsed = time.time() - t0
            _stats["total_time"] += elapsed
            data = resp.json()
            content = data.get("message", {}).get("content", "").strip()

            # Extract token counts from Ollama response
            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)
            _stats["total_tokens"] += eval_count + prompt_eval_count

            tok_s = eval_count / elapsed if elapsed > 0 else 0
            preview = content[:80].replace("\n", " ") if content else "(empty)"
            print(f"  [LLM #{call_num}] OK {elapsed:.1f}s | {prompt_eval_count}+{eval_count} tokens | {tok_s:.1f} tok/s | {preview}...")

            _stats["success"] += 1
            return content
        except requests.exceptions.Timeout:
            elapsed = time.time() - t0
            _stats["total_time"] += elapsed
            print(f"  [LLM #{call_num}] TIMEOUT after {elapsed:.0f}s")
            if attempt < 2:
                time.sleep(3)
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - t0
            _stats["total_time"] += elapsed
            print(f"  [LLM #{call_num}] CONNECTION ERROR: {e}")
            if attempt < 2:
                time.sleep(3)
        except Exception as e:
            elapsed = time.time() - t0
            _stats["total_time"] += elapsed
            print(f"  [LLM #{call_num}] ERROR: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(3)

    _stats["failed"] += 1
    print(f"  [LLM #{call_num}] FAILED after 3 attempts")
    return ""


def summarize(story):
    """Summarize a story in plain English."""
    source_note = ""
    if story.get("type") == "github":
        source_note = f"This is a GitHub repository. Stars: {story.get('stars', 'N/A')}. Language: {story.get('language', 'N/A')}."

    prompt = f"""Write a clear, concise 2-3 sentence summary of this item in plain English. Be informative and direct. No fluff.

Title: {story['title']}
Summary: {story.get('summary', 'No details available.')}
Source: {story.get('source', 'Unknown')}
{source_note}

Write ONLY the summary, no preamble:"""

    return _generate(prompt, max_tokens=200, label=f"summarize [{story.get('source', '?')}]")


def generate_headline(story):
    """Generate a clear, punchy headline."""
    prompt = f"""Rewrite this headline to be clear, concise, and attention-grabbing. Use title case. Keep it under 15 words. No Victorian language.

Original: {story['title']}
Context: {story.get('summary', '')[:200]}

Your rewrite:"""

    result = _generate(prompt, max_tokens=50, label=f"headline [{story['title'][:40]}]")
    # Clean up - remove quotes, extra whitespace
    result = result.strip('"\'').strip()
    # If the LLM just returned the original, flag it
    if not result or result.lower() == story["title"].lower():
        return story["title"]
    return result


def editorialize(stories):
    """Write an editor's column summarizing the day's themes."""
    briefs = []
    for i, s in enumerate(stories[:8], 1):
        briefs.append(f"{i}. {s['title']}: {s.get('summary', '')[:150]}")
    stories_text = "\n".join(briefs)

    prompt = f"""Write a short Editor's Column (3-4 sentences) identifying the overarching themes in today's AI and tech stories. Be insightful and direct. No Victorian language.

Today's stories:
{stories_text}

Write ONLY the editorial column, no title or preamble:"""

    return _generate(prompt, max_tokens=300, label="editorial")


def generate_telegram_digest(stories, editorial):
    """Generate a concise Telegram-friendly digest."""
    briefs = []
    for s in stories[:8]:
        briefs.append(f"- {s['title']}: {s.get('summary', '')[:100]}")
    stories_text = "\n".join(briefs)

    prompt = f"""You are writing a brief Telegram message digest for "The Daily Tensor" AI newsletter. Summarize the top stories in a punchy, readable format. Use emoji sparingly. Keep it under 300 words. Include the most important 5-6 stories.

Editor's take: {editorial}

Stories:
{stories_text}

Write the Telegram message:"""

    return _generate(prompt, max_tokens=400, label="telegram-digest")
