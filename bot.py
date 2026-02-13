import os
import asyncio
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== НАСТРОЙКИ ====
TOKEN = os.environ.get("TOKEN")
UPDATE_CHUNK_MIN = 5  # Обновление каждые 5 минут

active_timers = {}

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
    """Парсит время только из первого слова (напр. 29h5m)"""
    s = s.strip().lower()
    total, num = 0, ""
    for ch in s:
        if ch.isdigit():
            num += ch
        elif ch in ['d', 'h', 'm']:
            if not num: continue
            val = int(num); num = ""
            if ch == 'd': total += val * 1440
            elif ch == 'h': total += val * 60
            elif ch == 'm': total += val
    if num and not total: 
        total = int(num)
    return total

async def cmd_start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Пример: /start_timer 29h5m **Текст**")
        return
    
    # Берем время ТОЛЬКО из первого слова
    time_arg = context.args[0] 
    # Остальной текст — это подпись (поддерживает Markdown)
    label = "⏳ Осталось:" if len(context.args) == 1 else " ".join(context.args[1:])
    
    try:
        total_minutes = parse_to_minutes(time_arg)
        if total_minutes <= 0: raise ValueError
    except:
        await update.message.reply_text("❌ Ошибка формата! Пишите: /start_timer 29h4m Текст")
        return
    
    if chat_id in active_timers:
        active_timers[chat_id].cancel()

    # Отправляем сообщение с поддержкой Markdown
    msg = await update.message.reply_text(
        f"{label} {humanize_minutes(total_minutes)}",
        parse_mode=ParseMode.MARKDOWN
    )

    async def run_timer(minutes, message_id, current_label):
        try:
            while minutes > 0:
                await asyncio.sleep(UPDATE_CHUNK_MIN * 60)
                minutes -= UPDATE_CHUNK_MIN
                if minutes < 0: minutes = 0
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id, 
                        message_id=message_id,
                        text=f"{current_label} {humanize_minutes(minutes)}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception: break 
            if minutes <= 0:
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id, 
                        message_id=message_id, 
                        text=f"{current_label} ✅ Время вышло!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except: pass
        except asyncio.CancelledError:
            pass

    active_timers[chat_id] = asyncio.create_task(run_timer(total_minutes, msg.message_id, label))

# Health Server для Railway
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def main():
    if not TOKEN:
        return
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start_timer", cmd_start_timer))
    app.run_polling()

if __name__ == "__main__":
    main()
