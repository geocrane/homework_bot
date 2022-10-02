import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import ServerError, ServiceDenaied, StatusCodeError

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TOKENS = ["TELEGRAM_TOKEN", "PRACTICUM_TOKEN", "TELEGRAM_CHAT_ID"]
RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
HOMEWORK_VERDICTES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}
NETWORK_ERROR = (
    "Сбой сети {error} \nАдрес: {url}, " "headers: {headers}, params: {params}"
)
STATUS_CODE_ERROR = (
    "Неверный код возврата: {code}.\nАдрес: {url}, "
    "headers: {headers}, params: {params}"
)
SERVISE_DENAIED_ERROR = (
    "Отказ в обслуживании. {key}:{error} \nАдрес: {url}, "
    "headers: {headers}, params: {params}"
)
NOT_DICT_ERROR = "Тип данных ответа {type}. Ожидается dict"
NOT_LIST_ERROR = "Неверный тип объекта. Ожидается: list. Получен: {type}"
NO_KEY_ERROR = "Отсутствует ключ 'homeworks'"
NO_HOMEWORK_STATUS = "Неизвестный статус: {status}"
NO_SUCH_TOKEN = "Отсутствует обязательный токен {token}"
NO_ANY_TOKEN = "Отсутствует один из обязательных токенов"
STATUS_CHANGE = 'Изменился статус проверки работы "{homework}". {status}'
RESPONSE_JSON_ERRORS = ["code", "error"]
SEND_MESSAGE = "Отправлено сообщение: {message}"
MESSAGE_FAILED = "Не удалось отправить сообщение. chat_id: {chat_id}"
ERROR_MESSAGE = "Ошибка! {error}"


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
    request_data = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = requests.get(**request_data)
    except requests.exceptions.RequestException as error:
        raise ServerError(
            NETWORK_ERROR.format(exception=error, **request_data)
        )
    if not response.status_code == 200:
        raise StatusCodeError(
            STATUS_CODE_ERROR.format(code=response.status_code, **request_data)
        )
    response = response.json()
    for key in RESPONSE_JSON_ERRORS:
        if key in response:
            raise ServiceDenaied(
                SERVISE_DENAIED_ERROR.format(
                    key=key, error=response[key], **request_data
                )
            )
    return response


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API, приведенный к типам
    данных Python. Если ответ API соответствует ожиданиям, то функция должна
    вернуть список домашних работ (он может быть и пустым), доступный в ответе
    API по ключу 'homeworks'.
    """
    if not isinstance(response, dict):
        raise TypeError(NOT_DICT_ERROR.format(type=type(response)))
    if "homeworks" not in response:
        raise KeyError(NO_KEY_ERROR)
    homeworks = response["homeworks"]
    if not isinstance(homeworks, list):
        raise TypeError(NOT_LIST_ERROR.format(type=type(homeworks)))
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
        raise ValueError(NO_HOMEWORK_STATUS.format(status=status))
    return STATUS_CHANGE.format(
        homework=name, status=HOMEWORK_VERDICTES[status]
    )


def check_tokens():
    """Проверяет доступность необходимых переменных окружения."""
    bool_value = True
    for token in TOKENS:
        if not globals()[token]:
            logging.critical(NO_SUCH_TOKEN.format(token=token))
            bool_value = False
    return bool_value


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError(NO_ANY_TOKEN)
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    saved_message = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                continue
            message = parse_status(homeworks[0])
            if message != saved_message:
                send_message(bot, message)
                saved_message = message
                current_timestamp = response.get(
                    "current_date", current_timestamp
                )
        except Exception as error:
            logging.error(ERROR_MESSAGE.format(error=error))
            if str(error) == saved_message:
                continue
            try:
                send_message(bot, str(error))
                saved_message = str(error)
            except Exception:
                logging.error(
                    MESSAGE_FAILED.format(
                        chat_id=TELEGRAM_CHAT_ID
                    ),
                    exc_info=True,
                )
        finally:
            time.sleep(RETRY_TIME)


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            RotatingFileHandler(
                __file__ + ".log", maxBytes=5000000, backupCount=5
            ),
            logging.StreamHandler(),
        ],
        format=(
            "[%(asctime)s][%(levelname)s][str: %(lineno)d]"
            "[func: %(funcName)s] > %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    main()
