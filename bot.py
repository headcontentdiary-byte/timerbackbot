import os
import asyncio
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== НАСТРОЙКИ ====
TOKEN = os.environ.get("TOKEN")
UPDATE_CHUNK_MIN = 60  # Интервал обновления (60 минут)

# Временное хранилище (помните: при перезагрузке сервера данные обнулятся)
active_timers = {}

# ---------- УТИЛИТЫ ----------
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
    if s.isdigit():
        val = int(s)
        if val <= 0: raise ValueError("Число должно быть больше 0")
        return val
    
    total, num = 0, ""
    for ch in s:
        if ch.isdigit():
            num += ch
            continue
        if not num: continue
        val = int(num); num = ""
        if ch == "d": total += val * 1440
        elif ch == "h": total += val * 60
        elif ch == "m": total += val
    if num: total += int(num)
    if total <= 0: raise ValueError("Неверный формат")
    return total

# ---------- КОМАНДЫ ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 **Бот-таймер запущен**\n\n"
        "Команды:\n"
        "`/start_timer 3d Текст` — запуск на 3 дня\n"
        "`/stop_timer` — остановить текущий таймер",
        parse_mode="Markdown"
    )

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in active_timers:
        active_timers[chat_id].cancel()
        del active_timers[chat_id]
        await update.message.reply_text("🛑 Таймер остановлен.")
    else:
        await update.message.reply_text("Нет активных таймеров.")

async def cmd_start_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Пример: `/start_timer 24h До конца осталось:`", parse_mode="Markdown")
        return

    duration_arg = context.args[0]
    label = "⏳ Осталось:" if len(context.args) == 1 else " ".join(context.args[1:])
    
    try:
        total_minutes = parse_to_minutes(duration_arg)
    except Exception as e:
        await update.message.reply_text(f"Ошибка в формате времени: {e}")
        return

    # Отменяем старый таймер, если он есть
    if chat_id in active_timers:
        active_timers[chat_id].cancel()

    msg = await update.message.reply_text(f"{label} {humanize_minutes(total_minutes)}")

    async def run_timer(minutes, message_id):
        try:
            while minutes > 0:
                chunk = min(minutes, UPDATE_CHUNK_MIN)
                await asyncio.sleep(chunk * 60)
                minutes -= chunk
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"{label} {humanize_minutes(minutes)}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка редактирования: {e}")
                    break
            if minutes <= 0:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"{label} ✅ Время вышло!")
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(run_timer(total_minutes, msg.message_id))
    active_timers[chat_id] = task

# ---------- HEALTH SERVER (для Railway) ----------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def main():
    if not TOKEN:
        print("Ошибка: TOKEN не найден в переменных окружения!")
        return
    
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop_timer", cmd_stop))
    app.add_handler(CommandHandler("start_timer", cmd_start_timer))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
