import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from exceptions import ApiException, NotKnownException, TokenException

import requests
import telegram
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s',
    filemode='w'
)

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат.
    Чат задан переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot и
    строку с текстом сообщения.
    """
    logging.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_status = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_status.status_code != HTTPStatus.OK:
        status_code = homework_status.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    return homework_status.json()


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API.
    Ответ приведен к типам данных Python.
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ (он может быть пустым), доступный в ответе
    API по ключу 'homeworks'
    """
    if type(response) is not dict:
        raise TypeError('Ответ API отличен от словаря')
    list_works = response['homeworks']
    homework = list_works[0]
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает всего один элемент из списка домашних
    работ. В случае успеха, функция возвращает подготовленную для отправки в
    Telegram строку, содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    if 'homework_name' not in homework:
        raise KeyError('Отсутсвует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутсвует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы.
    Если отсутствует хотя бы одна переменная окружения — функция должна
    вернуть False, иначе — True.
    """
    if all([TELEGRAM_TOKEN and PRACTICUM_TOKEN and TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    error_cache_message = ''
    if not check_tokens():
        logging.critical('Отсутствуют одна или несколько переменных окружения')
        raise TokenException(
            'Отсутствуют одна или несколько переменных окружения')
    while True:
        try:
            try:
                response = get_api_answer(current_timestamp)
            except ApiException as error:
                logging.error(f'Ошибка при запросе к основному API: {error}')
                raise ApiException(
                    f'Ошибка при запросе к основному API: {error}')
            except ValueError:
                logging.error('Ошибка парсинга ответа из формата json')
                raise ValueError('Ошибка парсинга ответа из формата json')

            current_timestamp = response.get('current_date')
            try:
                message = parse_status(check_response(response))
            except KeyError:
                logging.error('Ошибка словаря по ключу homeworks')
                raise KeyError('Ошибка словаря по ключу homeworks')
            except IndexError:
                logging.error('Список домашних работ пуст')
                raise IndexError('Список домашних работ пуст')
            if message != status:
                try:
                    send_message(bot, message)
                except telegram.error.TelegramError:
                    logging.error('Ошибка отправки сообщения в телеграм')
            time.sleep(RETRY_TIME)
        except NotKnownException as error:
            logging.error(error)
            message = f'Сбой в работе программы: {error}'
            if message != error_cache_message:
                send_message(bot, message)
                error_cache_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
