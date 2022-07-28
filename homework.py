import requests
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import telegram
from http import HTTPStatus

load_dotenv()
secret_token = os.getenv('TOKEN')
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s',
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log',
                              encoding='UTF-8',
                              maxBytes=50000000,
                              backupCount=5
                              )
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s'
)
handler.setFormatter(formatter)


PRACTICUM_TOKEN = 'AQAAAAAWe5TJAAYckV9qzB0DE0OVkaMYYkpBOSs'
TELEGRAM_TOKEN = secret_token
TELEGRAM_CHAT_ID = 1289576953

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
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Ошибка отправки сообщения в телеграм')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_status = requests.get(ENDPOINT, headers=HEADERS,
                                       params=params)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if homework_status.status_code != HTTPStatus.OK:
        status_code = homework_status.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    try:
        return homework_status.json()
    except ValueError:
        logger.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


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
    try:
        list_works = response['homeworks']
    except KeyError:
        logger.error('Ошибка словаря по ключу homeworks')
        raise KeyError('Ошибка словаря по ключу homeworks')
    try:
        homework = list_works[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
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
    if TELEGRAM_TOKEN and PRACTICUM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    error_cache_message = ''
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != status:
                send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            if message != error_cache_message:
                send_message(bot, message)
                error_cache_message = message
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
