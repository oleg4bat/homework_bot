import http
import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import OkStatusError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
TOKEN_NAMES = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID'
]

RETRY_PERIOD = 600
ONE_DAY = 86400
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
PARSE_MSG = 'Изменился статус проверки работы "{}". {}'


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверка наличия необходимых токенов."""
    for name in TOKEN_NAMES:
        if not globals()[name]:
            logging.critical(f'Нет необходимого токена {name}.')
            return False
        return True


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logging.error(f'Сбой при отправке сообщения в чат - {error}',
                      exc_info=True)
        raise Exception(error)
    else:
        logging.debug('Сообщеие отправленно успешно.', exc_info=True)


def get_api_answer(timestamp: int) -> dict:
    """Получение ответа от API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != http.HTTPStatus.OK:
            logging.error('API домашки возвращает код, отличный от 200',
                          exc_info=True)
            raise OkStatusError('API домашки возвращает код, отличный от 200')
        if set(response.json()) == {'error', 'code'}:
            logging.error('API домашки возвращает код, отличный от 200',
                          exc_info=True)
            error = response.json()['error']
            code = response.json()['code']
            raise OkStatusError(error, code)
        return response.json()
    except requests.URLRequired():
        logging.error('API недоступен:', exc_info=True)
        raise requests.RequestException('API недоступен: ')


def check_response(response: dict) -> bool:
    """проверяет ответ API на соответствие документации."""
    keys = ('homeworks', 'current_date')
    if not isinstance(response, dict):
        logging.error('API выдает неверные данные.', exc_info=True)
        raise TypeError('Тип "response" не словарь')
    if not isinstance(response.get('homeworks'), list):
        logging.error('API выдает неверные данные.', exc_info=True)
        raise TypeError('В API домашка не стисок.')
    if 'homeworks' not in response:
        logging.error('API выдает неверные данные.', exc_info=True)
        raise KeyError('В API нет ключа домашки.')
    if keys not in response:
        logging.error('в API нет необходимых ключей.', exc_info=True)
        return False
    return True


def parse_status(homework: dict) -> str:
    """Извлекает информацию о статусе конкретной домашной работе."""
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logging.error('Домашка с неизвестным статусом', exc_info=True)
        raise KeyError('Домашка с неизвестным статусом')
    verdict = HOMEWORK_VERDICTS[status]
    if 'homework_name' not in homework:
        raise KeyError('Неизвестная домашка')
    homework_name = homework.get('homework_name')
    return PARSE_MSG.format(homework_name, verdict)


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        return print('Программа принудительно остановлена.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - ONE_DAY
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
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='bot.log',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    main()
