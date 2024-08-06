import time

import requests
import telegram

from environs import Env

URL = 'https://dvmn.org/api/long_polling/'


def fetch_updates(url, headers, timestamp, timeout):
    params = {'timestamp': timestamp}
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def send_message(bot, tg_chat_id, lesson_title, lesson_url, lesson_negative):
    message = (f"Новая проверка работы!\n\n"
               f"Урок: {lesson_title}\n"
               f"Ссылка: {lesson_url}\n")
    if lesson_negative:
        message += "Результат: Всё правильно! Делай дальше."
    else:
        message += "Результат: Урок не принят."
    bot.send_message(chat_id=tg_chat_id, text=message)


def main():
    env = Env()
    env.read_env()
    bot = telegram.Bot(token=env.str("TG_BOT_TOKEN"))
    headers = {
        'Authorization': f'Token {env.str("API_DEVMAN_TOKEN")}'
    }
    tg_chat_id = env.str("TG_CHAT_ID")
    attempt = 0
    timeout = 5
    timestamp = None
    while True:
        try:
            updates = fetch_updates(URL, headers, timestamp, timeout)
            if updates['new_attempts']:
                for new_attempt in updates['new_attempts']:
                    lesson_title = new_attempt['lesson_title']
                    lesson_url = new_attempt['lesson_url']
                    lesson_negative = new_attempt['is_negative']
                    send_message(bot, tg_chat_id, lesson_title, lesson_url, lesson_negative)
                timestamp = updates['new_attempts'][-1]['timestamp']
            else:
                timestamp = updates['last_attempt_timestamp']
        except requests.exceptions.ReadTimeout:
            print('Время ожидания запроса истекло, завершаю долгое опрашивание...')
        except requests.ConnectionError as err:
            print(f"Ошибка соединения - попытка {attempt + 1}: {err}")
            time.sleep(10)
            attempt += 1
        except requests.exceptions.RequestException as e:
            print(f'Ошибка при долгом опрашивании: {e}')


if __name__ == "__main__":
    main()
