import threading
import telebot
from database import db
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.bot = None
        self.thread = None
        self._stop_event = threading.Event()

    def start_bot(self):
        config = db.get_config()
        token = config.get("bot_token")
        is_running = config.get("is_running", False)

        if not token or not is_running:
            logger.info("Bot is not set to run or token is missing.")
            return False

        if self.thread and self.thread.is_alive():
            logger.info("Bot is already running.")
            return True

        self._stop_event.clear()
        self.bot = telebot.TeleBot(token)
        
        from bot_handlers import register_handlers
        register_handlers(self.bot)

        logger.info("Starting bot polling thread...")
        self.thread = threading.Thread(target=self._run_polling, daemon=True)
        self.thread.start()
        return True

    def _run_polling(self):
        # We loop just in case it crashes, but telebot handles internal errors if none_stop=True
        while not self._stop_event.is_set():
            try:
                self.bot.polling(none_stop=True)
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                time.sleep(3)
        logger.info("Bot polling thread stopped.")

    def stop_bot(self):
        logger.info("Stopping bot...")
        self._stop_event.set()
        if self.bot:
            self.bot.stop_polling()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        self.bot = None
        self.thread = None
        return True

    def restart_bot(self):
        self.stop_bot()
        return self.start_bot()

bot_manager = BotManager()
