import inspect
import logging
import os
import time
import requests

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from requests import (
    ReadTimeout,
    ConnectTimeout,
    HTTPError,
    Timeout,
    ConnectionError,
)
from telegram import Bot

from exceptions import ServerError

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

SEND_MESSAGE = "Отправлено сообщение: {message}"
STATUS_CODE_ERR_MSG = (
    "Ошибка! Код возврата: {code}.\nАдрес: {endpoint}, "
    "headers: {headers}, timestamp: {timestamp}"
)
NOT_DICT_ERR_MSG = "Тип ответа не является словарем"
NOT_LIST_ERR_MSG = "Неверный тип объекта. Ожидается: list. Получен: {type}"
NO_ATTR_ERR_MSG = (
    "Отсутствует необходимый атрибут. "
    "Ожидается: 'homeworks'. Присутствуют: {attributes} "
)
NO_HOMEWORK_STATUS = (
    "Неизвестный статус. Ожидается: {valid_statuses} Получен: {status}"
)
STATUS_CHANGE_MSG = 'Изменился статус проверки работы "{homework}". {status}'


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат определяемый TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot и строку с текстом
    сообщения.
    """
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info(SEND_MESSAGE.format(message=message))


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата JSON к типам
    данных Python.
    """
    params = {"from_date": current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except (
        ConnectTimeout,
        HTTPError,
        ReadTimeout,
        Timeout,
        ConnectionError,
    ) as err:
        pass
        logging.error(err)
    if not response.status_code == 200:
        raise ServerError(
            STATUS_CODE_ERR_MSG.format(
                code=response.status_code,
                endpoint=ENDPOINT,
                headers=HEADERS,
                timestamp=current_timestamp,
            )
        )
    response = response.json()
    logging.info(response)
    return response


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API, приведенный к типам
    данных Python. Если ответ API соответствует ожиданиям, то функция должна
    вернуть список домашних работ (он может быть и пустым), доступный в ответе
    API по ключу 'homeworks'.
    """
    if not isinstance(response, dict):
        raise TypeError(NOT_DICT_ERR_MSG)
    if "homeworks" not in response:
        raise AttributeError(
            NO_ATTR_ERR_MSG.format(attributes=list(response.keys()))
        )
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        raise TypeError(
            NOT_LIST_ERR_MSG.format(
                type=inspect.getmro(type(homeworks))[-2].__name__
            )
        )
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ее статус.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_VERDICTES.
    """
    status = homework["status"]
    name = homework["homework_name"]
    if status not in HOMEWORK_VERDICTES:
        raise AttributeError(
            NO_HOMEWORK_STATUS.format(
                valid_statuses=list(HOMEWORK_VERDICTES.keys()), status=status
            )
        )
    return STATUS_CHANGE_MSG.format(
        homework=name, status=HOMEWORK_VERDICTES.get(status)
    )


def check_tokens():
    """Проверяет доступность необходимых переменных окружения."""
    if not TELEGRAM_CHAT_ID:
        return False
    elif not TELEGRAM_TOKEN:
        return False
    elif not PRACTICUM_TOKEN:
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = 0
        saved_message = None
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if not len(homeworks) == 0:
                    message = parse_status(homeworks[0])
                    if message != saved_message:
                        send_message(bot, message)
                        saved_message = message
                        current_timestamp = response.get(
                            "current_date", current_timestamp
                        )
            except Exception as err:
                logging.error(err)
                if str(err) != saved_message:
                    send_message(bot, str(err))
                    saved_message = str(err)
            time.sleep(RETRY_TIME)
            continue


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            RotatingFileHandler(
                __file__ + ".log", maxBytes=5000000, backupCount=5
            ),
        ],
        format=(
            "[%(asctime)s][%(levelname)s][str: %(lineno)d]"
            "[func: %(funcName)s] > %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    main()
