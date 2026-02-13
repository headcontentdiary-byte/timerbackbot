import os, asyncio, threading, logging, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.ext import Application

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TOKEN")

CHANNEL_ID = "@ProstoMeditation"
# ДЕДЛАЙН: 14 февраля 2026, 23:59:00 по Москве (UTC+3)
DEADLINE = datetime.datetime(2026, 2, 14, 23, 59, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=3)))

# ТЕКСТ: Ссылка снова ЖИРНАЯ <b>...</b>
TEXT = "<b>Скидка 83% скоро сгорит! Такого предложения больше НЕ БУДЕТ! Зафиксируйте самую выгодную цену на 2027 год.</b>\n\n<b><a href='https://wow.prostoapp.ru/valentine26'>👉 ЗАБРАТЬ СКИДКУ</a></b>"

def get_remaining_time():
    now = datetime.datetime.now(datetime.timezone.utc)
    remaining = DEADLINE - now
    if remaining.total_seconds() <= 0:
        return None
    
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0: parts.append(f"{days} д")
    if hours > 0 or days > 0: parts.append(f"{hours} ч")
    parts.append(f"{minutes} м")
    return " ".join(parts)

async def run_timer_task(app: Application):
    await asyncio.sleep(5) # Пауза для запуска бота
    try:
        time_str = get_remaining_time() or "0 м"
        sent_msg = await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"⌛ <b>Осталось: {time_str}</b>\n{TEXT}",
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        msg_id = sent_msg.message_id
        logging.info(f"Создан новый пост ID: {msg_id}")
    except Exception as e:
        logging.error(f"Не удалось отправить пост: {e}")
        return

    while True:
        await asyncio.sleep(300) # Обновление каждые 5 минут
        time_str = get_remaining_time()
        try:
            if time_str:
                await app.bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=msg_id,
                    text=f"⌛ <b>Осталось: {time_str}</b>\n{TEXT}",
                    parse_mode=ParseMode.HTML,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            else:
                await app.bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=msg_id,
                    text=f"✅ <b>Акция завершена!</b>\n{TEXT}",
                    parse_mode=ParseMode.HTML
                )
                break
        except Exception as e:
            logging.error(f"Ошибка обновления: {e}")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

def main():
    if not TOKEN: return
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever(), daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # Исправленный запуск фоновой задачи
    loop = asyncio.get_event_loop()
    loop.create_task(run_timer_task(app))
    
    app.run_polling()

if __name__ == "__main__":
    main()
