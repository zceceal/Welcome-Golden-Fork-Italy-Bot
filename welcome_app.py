# welcome_app.py — Telegram "welcome" bot via webhook (Railway-ready)

from telebot import TeleBot, types
from flask import Flask, request, abort
import os
import html  # HTML escaping

# --- ENV ---
BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")   # set in Railway Variables
RAILWAY_URL = os.getenv("RAILWAY_URL")          # e.g. https://your-app.up.railway.app
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is not set!")

# Use HTML parse mode for safer mentions
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

app = Flask(__name__)

# --- Utility: internal "t.me/c" id from chat_id ---
def internal_chat_id(chat_id: int) -> str:
    """
    For supergroups/channels, t.me/c/<internal>/<msg_id> uses chat_id without the '-100' prefix.
    Example: chat_id = -1003056610802 -> internal '3056610802'
    """
    s = str(chat_id)
    return s[4:] if s.startswith("-100") else s.lstrip("-")

# Prefer public @username link if available; fallback to t.me/c/…
def chat_link_base(chat):
    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}"
    return f"https://t.me/c/{internal_chat_id(chat.id)}"

# --- WELCOME HANDLER ---
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    base = chat_link_base(message.chat)

    # Inline buttons (update message IDs with yours)
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("ℹ️ Info Servizio", url=f"{base}/2"),
        types.InlineKeyboardButton("⭐ Recensioni", url=f"{base}/3")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 Giveaway", url=f"{base}/13"),
        types.InlineKeyboardButton("📢 Annunci", url=f"{base}/7")
    )
    markup.add(
        types.InlineKeyboardButton("🍴 Prenota con 50€ di sconto", url="https://t.me/axel_fork_bot")
    )

    # Welcome each new member
    for new_member in message.new_chat_members:
        display_name = (new_member.first_name or "ospite").strip()
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(display_name)}</a>'

        welcome_text = (
            f"✨ Benvenutə in Golden Fork, {mention}! ✨\n"
            f"Il posto dove ogni prenotazione significa £50 di risparmio.\n\n"
            f"<b>Sezioni principali</b>:\n"
            f"ℹ️ Info Servizio | ⭐ Recensioni | 🎁 Giveaway | 📢 Annunci\n\n"
            f"👉 Per iniziare, scegli un’opzione qui sotto:"
        )

        kwargs = {}
        if getattr(message, "message_thread_id", None):
            kwargs["message_thread_id"] = message.message_thread_id

        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=markup,
            disable_web_page_preview=True,
            **kwargs
        )

# --- Flask / webhook ---
@app.get("/health")
def health():
    return "ok", 200

@app.post(f"/webhook/{BOT_TOKEN}")
def telegram_webhook():
    if request.headers.get("content-type") == "application/json":
        update = types.Update.de_json(request.get_data(as_text=True))
        bot.process_new_updates([update])
        return "OK", 200
    abort(403)

if __name__ == "__main__":
    if not RAILWAY_URL:
        raise ValueError("❌ RAILWAY_URL is not set! (e.g., https://your-app.up.railway.app)")

    bot.remove_webhook()
    bot.set_webhook(
        url=f"{RAILWAY_URL}/webhook/{BOT_TOKEN}",
        drop_pending_updates=True,
        allowed_updates=["message"]
    )

    port = int(os.getenv("PORT", "8080"))
    print(f"🤖 Bot di benvenuto attivo via webhook sulla porta {port}…")
    app.run(host="0.0.0.0", port=port)
