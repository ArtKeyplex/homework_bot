import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (ApiException, BotException, NotKnownException,
                        StatusException)

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
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except BotException:
        raise BotException('Ошибка отправки сообщения в телеграм')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except ApiException as error:
        raise ApiException(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        raise Exception(f'Ошибка {response.status_code}')
    try:
        return response.json()
    except ValueError:
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API.
    Ответ приведен к типам данных Python.-
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ (он может быть пустым), доступный в ответе
    API по ключу 'homeworks'
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ API отличен от словаря')
    try:
        list_works = response['homeworks']
    except KeyError:
        raise KeyError('Ошибка словаря по ключу homeworks')
    try:
        homework = list_works[0]
    except IndexError:
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
        raise StatusException(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, необходимых для работы.
    Если отсутствует хотя бы одна переменная окружения — функция должна
    вернуть False, иначе — True.

    """
    return all([TELEGRAM_TOKEN and PRACTICUM_TOKEN and TELEGRAM_CHAT_ID])


def main():  # noqa
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    status = ''
    if not check_tokens():
        logging.critical('Отсутствуют одна или несколько переменных окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != status:
                logging.info(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
                send_message(bot, message)
        except BotException:
            logging.error('Ошибка отправки сообщения в телеграм')
            send_message(bot, 'Ошибка отправки сообщения в телеграм')
        except ApiException as error:
            logging.error(f'Ошибка при запросе к основному API: {error}')
            send_message(bot, f'Ошибка при запросе к основному API: {error}')
        except ValueError:
            logging.error('Ошибка парсинга ответа из формата json')
            send_message(bot, 'Ошибка парсинга ответа из формата json')
        except NotKnownException:
            logging.error(f'Ошибка {NotKnownException}')
            send_message(bot, f'Ошибка {NotKnownException}')
        except KeyError:
            logging.error('Ошибка словаря по ключу homeworks')
            send_message(bot, 'Ошибка словаря по ключу homeworks')
        except IndexError:
            logging.error('Список домашних работ пуст')
            send_message(bot, 'Список домашних работ пуст')
        except StatusException:
            logging.error(f'Статус работы: {StatusException}')
            send_message(bot, f'Статус работы: {StatusException}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
