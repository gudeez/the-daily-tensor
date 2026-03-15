import requests
from config import TG_BOT_TOKEN, TG_CHANNEL_ID


def send_edition_to_telegram(digest_text, edition_date):
    """Send a digest message to the configured Telegram channel."""
    if not TG_BOT_TOKEN or not TG_CHANNEL_ID:
        print("[Telegram] No bot token or channel ID configured, skipping")
        return False

    header = f"📰 *THE DAILY TENSOR*\n_{edition_date}_\n\n"
    message = header + digest_text

    # Telegram message limit is 4096 chars
    if len(message) > 4096:
        message = message[:4090] + "\n..."

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TG_CHANNEL_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        data = resp.json()
        if data.get("ok"):
            print(f"[Telegram] Sent to {TG_CHANNEL_ID}")
            return True
        else:
            print(f"[Telegram] API error: {data.get('description', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"[Telegram] Failed to send: {e}")
        return False
