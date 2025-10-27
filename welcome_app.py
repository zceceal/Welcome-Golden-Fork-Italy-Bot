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

# --- SEZIONI (aggiorna con i tuoi link Telegram) ---
SECTION_LINKS = {
    "info":                     "https://t.me/c/3239080709/2/1",
    "discounts":                "https://t.me/c/3239080709/11/1",
    "reviews":                  "https://t.me/c/3239080709/3/1",
    "giveaways":                "https://t.me/c/3239080709/13/1",
    "announce":                 "https://t.me/c/3239080709/7/1",
}

# --- Utility: internal "t.me/c" id from chat_id ---
def internal_chat_id(chat_id: int) -> str:
    """
    Per supergruppi/canali, t.me/c/<internal>/<msg_id> usa chat_id senza il prefisso '-100'.
    Esempio: chat_id = -1003056610802 -> internal '3239080709'
    """
    s = str(chat_id)
    return s[4:] if s.startswith("-100") else s.lstrip("-")

# Preferisci il link pubblico @username se disponibile; altrimenti t.me/c/…
def chat_link_base(chat):
    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}"
    return f"https://t.me/c/{internal_chat_id(chat.id)}"

# Variabile globale per memorizzare l’ID del messaggio fissato
PINNED_MSG_ID = None

# --- GESTORE DI BENVENUTO ---
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    global PINNED_MSG_ID

    print(f"👋 New members: {[m.id for m in message.new_chat_members]}")

    # Colleziona i nomi dei nuovi membri
    new_names = []
    for new_member in message.new_chat_members:
        display_name = (new_member.first_name or "ospite").strip()
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(display_name)}</a>'
        new_names.append(mention)

    joined_text = ", ".join(new_names)

    # 🇮🇹 Messaggio di benvenuto
    welcome_text = (
        f"✨ Benvenuti in Golden Fork, {joined_text}! ✨\n"
        f"Il posto dove ogni prenotazione significa 50€ di risparmio.\n\n"
        f"👉 Per iniziare, scegli un’opzione qui sotto:"
    )

    # Calcola il link base per la chat (link pubblico se esiste, altrimenti t.me/c)
    base = chat_link_base(message.chat)

    # Pulsanti principali
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("ℹ️ Info Servizio",   url=SECTION_LINKS["info"]),
        types.InlineKeyboardButton("❗ Sconti Multipli", url=SECTION_LINKS["discounts"])
    )
    markup.add(
        types.InlineKeyboardButton("⭐ Recensioni",     url=SECTION_LINKS["reviews"]),
        types.InlineKeyboardButton("🎁 Giveaway",       url=SECTION_LINKS["giveaways"])
    )
    markup.add(
        types.InlineKeyboardButton("📢 Annunci", url=SECTION_LINKS["announce"])
    )
    markup.add(
        # Deep link che apre il bot e avvia il flusso
        types.InlineKeyboardButton("🍴 Prenota con 50€ di sconto",
                                url="https://t.me/GoldenForkBookingsBot?start=reserve")
    )

    kwargs = {}
    if getattr(message, "message_thread_id", None):
        kwargs["message_thread_id"] = message.message_thread_id

    # Se non esiste ancora un messaggio fissato → creane uno
    if PINNED_MSG_ID is None:
        sent = bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=markup,
            disable_web_page_preview=True,
            disable_notification=True,
            **kwargs
        )
        PINNED_MSG_ID = sent.message_id

        # ✅ Prova a fissare il messaggio di benvenuto
        try:
            bot.pin_chat_message(message.chat.id, PINNED_MSG_ID, disable_notification=True)
            print(f"📌 Messaggio fissato con successo {PINNED_MSG_ID}")
        except Exception as e:
            print(f"⚠️ Errore nel fissare il messaggio: {e}")

    else:
        # Modifica il messaggio fissato esistente
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=PINNED_MSG_ID,
                text=welcome_text,
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"⚠️ Impossibile modificare il messaggio fissato: {e}")

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
        raise ValueError("❌ RAILWAY_URL non impostato! (es. https://your-app.up.railway.app)")

    # Reset & set webhook
    bot.remove_webhook()
    bot.set_webhook(
        url=f"{RAILWAY_URL}/webhook/{BOT_TOKEN}",
        drop_pending_updates=True,
        allowed_updates=["message"]
    )

    port = int(os.getenv("PORT", "8080"))
    print(f"🤖 Bot di benvenuto attivo via webhook sulla porta {port}…")
    app.run(host="0.0.0.0", port=port)
