import os, asyncio, threading, logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TOKEN")
UPDATE_CHUNK_MIN = 5 
CHANNEL_ID = "@ProstoMeditation" 

def humanize_minutes(total_min: int) -> str:
    if total_min <= 0: return "0 м"
    d, rem = divmod(total_min, 1440)
    h, m = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d} д")
    if h: parts.append(f"{h} ч")
    if m or not parts: parts.append(f"{m} м")
    return " ".join(parts)

def parse_to_minutes(s: str) -> int:
    s = s.strip().lower()
    total, num = 0, ""
    for ch in s:
        if ch.isdigit(): num += ch
        elif ch in ['d', 'h', 'm']:
            if not num: continue
            val = int(num); num = ""
            if ch == 'd': total += val * 1440
            elif ch == 'h': total += val * 60
            elif ch == 'm': total += val
    if num and not total: total = int(num)
    return total

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Формат: /run [ID сообщения] [время] [текст]
    if len(context.args) < 3: return
    msg_id = int(context.args[0])
    minutes = parse_to_minutes(context.args[1])
    label = " ".join(context.args[2:])
    
    await update.message.reply_text(f"🚀 Запустил обновление поста {msg_id}")

    while minutes > 0:
        try:
            await context.bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=msg_id,
                text=f"⌛ <b>Осталось: {humanize_minutes(minutes)}</b>\n{label}",
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
        except Exception as e:
            logging.error(f"Ошибка: {e}")
        await asyncio.sleep(UPDATE_CHUNK_
