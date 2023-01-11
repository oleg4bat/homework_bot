import os

import telegram
import time
import sys
import requests
import logging
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='bot.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def check_tokens():
    """Проверка наличия необходимых токенов."""
    tokens = (globals()['PRACTICUM_TOKEN'],
              globals()['TELEGRAM_CHAT_ID'],
              globals()['TELEGRAM_TOKEN'],
              )
    if not all(tokens):
        logging.critical('Нет необходимых токенов')
        return False
    else:
        return True


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as TGerrors:
        logging.error(f'Сбой при отправке сообщения в чат - {TGerrors}')
        raise Exception(TGerrors)
    else:
        logging.debug('Сообщеие отправленно успешно.')


def get_api_answer(timestamp):
    """Получение ответа от API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            logging.error('API домашки возвращает код, отличный от 200',
                          exc_info=True)
            raise Exception
        return response.json()
    except requests.URLRequired():
        logging.error('API недоступен:', exc_info=True)
        raise requests.RequestException


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    keys = ('homeworks', 'current_date',)
    if not isinstance(response, dict):
        logging.error('API выдает неверные данные.', exc_info=True)
        raise TypeError('Тип "response" не словарь')
    if not isinstance(response.get('homeworks'), list):
        logging.error('API выдает неверные данные.', exc_info=True)
        raise TypeError('С API что-то не так.')
    if 'homeworks' not in response:
        logging.error('API выдает неверные данные.', exc_info=True)
        raise KeyError('С API что-то не так.')
    if keys not in response:
        logging.error('API выдает неверные данные.', exc_info=True)
        return False
    else:
        True


def parse_status(homework):
    """Извлекает информацию о статусе конкретной домашной работе."""
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logging.error('Домашка с неизвестным статусом')
        raise KeyError('Домашка с неизвестным статусом')
    verdict = HOMEWORK_VERDICTS[status]
    if 'homework_name' not in homework:
        raise KeyError('Неизвестная домашка')
    homework_name = homework.get('homework_name')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Программа принудительно остановлена.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 86400
    old_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if not response.get('homeworks')[0]:
                raise KeyError('Домашку еще не начали проверять.')
            else:
                homework = response.get('homeworks')[0]
                message = parse_status(homework)
                if old_message != message:
                    send_message(bot, message)
                    old_message = message

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
