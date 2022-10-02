import logging
import os
import time
import traceback
import requests
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from telegram import Bot

from exceptions import MessageError, ServerError, ServiceDenaied

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
    "Сбой сети. \nАдрес: {endpoint}, " "headers: {headers}, params: {params}"
)
STATUS_CODE_ERROR = (
    "Неверный код возврата: {code}.\nАдрес: {endpoint}, "
    "headers: {headers}, params: {params}"
)
SERVISE_DENAIED_ERROR = (
    "Отказ в обслуживании.\nАдрес: {endpoint}, "
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
MESSAGE_FAILED = "Не удалось отправить сообщение {message}, chat_id: {chat_id}"


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат определяемый TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot и строку с текстом
    сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(SEND_MESSAGE.format(message=message))
    except Exception:
        raise MessageError(
            MESSAGE_FAILED.format(message=message, chat_id=TELEGRAM_CHAT_ID)
        )


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата JSON к типам
    данных Python.
    """
    params = {"from_date": current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as error:
        raise error(
            NETWORK_ERROR.format(
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
            )
        )
    if not response.status_code == 200:
        raise ServerError(
            STATUS_CODE_ERROR.format(
                code=response.status_code,
                endpoint=ENDPOINT,
                headers=HEADERS,
                params=params,
            )
        )
    response = response.json()
    for key in RESPONSE_JSON_ERRORS:
        if key in response:
            raise ServiceDenaied(
                SERVISE_DENAIED_ERROR.format(
                    endpoint=ENDPOINT,
                    headers=HEADERS,
                    params=params,
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
    retry = 0
    while True:
        time.sleep(retry)
        retry = RETRY_TIME
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                time.sleep(RETRY_TIME)
                continue
            message = parse_status(homeworks[0])
            if message != saved_message:
                send_message(bot, message)
                saved_message = message
                current_timestamp = response.get(
                    "current_date", current_timestamp
                )
        except Exception:
            logging.error("", exc_info=True)
            error_message = traceback.format_exc(limit=None, chain=True)
            if error_message == saved_message:
                time.sleep(RETRY_TIME)
                continue
            try:
                send_message(bot, error_message)
            except Exception:
                logging.error(
                    MESSAGE_FAILED.format(
                        message=error_message, chat_id=TELEGRAM_CHAT_ID
                    ),
                    exc_info=True,
                )
            saved_message = error_message


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.DEBUG,
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
