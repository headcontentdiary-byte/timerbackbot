import os, asyncio, threading, logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.ext import Application

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TOKEN")

# НАСТРОЙКИ
CHANNEL_ID = "@ProstoMeditation"
MSG_ID = 6081
# Время с учетом деплоя (23ч 40м)
START_MINUTES = 1420 
TEXT = "<b>Скидка 83% скоро сгорит! Такого предложения больше НЕ БУДЕТ! Зафиксируйте самую выгодную цену на 2027 год.</b>\n\n<b><a href='https://wow.prostoapp.ru/valentine26'>👉 ЗАБРАТЬ СКИДКУ</a></b>"

async def run_forever(app):
    minutes = START_MINUTES
    while minutes > 0:
        try:
            h = minutes // 60
            m = minutes % 60
            time_str = f"{h} ч {m} м"
            
            await app.bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=MSG_ID,
                text=f"⌛ <b>Осталось: {time_str}</b>\n{TEXT}",
                parse_mode=ParseMode.HTML,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            logging.info(f"Успешно обновил пост {MSG_ID}")
        except Exception as e:
            logging.error(f"Ошибка обновления: {e}")
        
        await asyncio.sleep(300) 
        minutes -= 5

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

def main():
    if not TOKEN: return
    port = int(os.environ.get("PORT", 8080))
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever(), daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    loop = asyncio.get_event_loop()
    loop.create_task(run_forever(app))
    app.run_polling()

if __name__ == "__main__":
    main()
