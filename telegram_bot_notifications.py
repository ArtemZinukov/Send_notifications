import time
import logging
import traceback
import requests
import telegram
from environs import Env

URL = 'https://dvmn.org/api/long_polling/'

logger = logging.getLogger(__name__)


class TelegramLogsHandler(logging.Handler):
    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def fetch_updates(url, headers, timestamp, timeout):
    params = {'timestamp': timestamp}
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def send_message(lesson_title, lesson_url, lesson_negative, logger):
    message = (f"Новая проверка работы!\n\n"
               f"Урок: {lesson_title}\n"
               f"Ссылка: {lesson_url}\n"
               f"Результат: {'Всё правильно! Делай дальше.' if lesson_negative else 'Урок не принят.'}")
    logger.info(message)


def process_updates(updates, logger):
    if updates['new_attempts']:
        for new_attempt in updates['new_attempts']:
            lesson_title = new_attempt['lesson_title']
            lesson_url = new_attempt['lesson_url']
            lesson_negative = new_attempt['is_negative']
            send_message(lesson_title, lesson_url, lesson_negative, logger)
        return updates['new_attempts'][-1]['timestamp']
    return updates['last_attempt_timestamp']


def main():
    env = Env()
    env.read_env()

    tg_bot = telegram.Bot(token=env.str("TG_BOT_TOKEN"))
    tg_chat_id = env.str("TG_CHAT_ID")
    headers = {'Authorization': f'Token {env.str("API_DEVMAN_TOKEN")}'}

    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    telegram_handler = TelegramLogsHandler(tg_bot, tg_chat_id)
    telegram_handler.setLevel(logging.INFO)
    telegram_formatter = logging.Formatter('%(message)s')
    telegram_handler.setFormatter(telegram_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(telegram_handler)

    timeout = 90
    timestamp = None
    logger.info('Запуск бота')

    while True:
        try:
            updates = fetch_updates(URL, headers, timestamp, timeout)
            timestamp = process_updates(updates, logger)
        except requests.exceptions.ReadTimeout:
            logger.warning('Время ожидания запроса истекло, завершаю долгое опрашивание...')
        except requests.ConnectionError as err:
            logger.error(f"Ошибка соединения: {err}")
            time.sleep(10)
        except requests.exceptions.RequestException as e:
            logger.error(f'Ошибка при долгом опрашивании: {e}')
        except Exception as e:
            logger.error(f'Ошибка: {e}')
            logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
