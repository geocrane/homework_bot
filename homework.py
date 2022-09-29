import logging
import os
import time
import requests

from dotenv import load_dotenv
from telegram import Bot

from exceptions import (
    EmptyList,
    MessageError,
    ResponseError,
    ServerError,
    StatusError,
)

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG, format="%(levelname)s, %(asctime)s, %(message)s"
)

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат определяемый TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot и строку с текстом
    сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Отправлено сообщение: "{message}"')
    except MessageError:
        logging.error(f'Не удалось отправить сообщение: "{message}"')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку. В случае успешного
    запроса должна вернуть ответ API, преобразовав его из формата JSON к типам
    данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if not response.status_code == 200:
        raise ServerError(logging.error("Сервер API недоступен"))
    response = response.json()
    return response


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API, приведенный к типам
    данных Python. Если ответ API соответствует ожиданиям, то функция должна
    вернуть список домашних работ (он может быть и пустым), доступный в ответе
    API по ключу 'homeworks'.
    """
    if type(response) == list:
        response = response[0]
    elif not type(response.get("homeworks")) == list:
        logging.error("Домашки приходят не в виде списка")
        raise ResponseError
    elif "homeworks" not in response and "current_date" not in response:
        logging.error("Отсутствуют ожидаемые ключи в ответе API")
        raise ResponseError
    return response.get("homeworks")


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе ее статус.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_STATUSES.
    """
    if ("status" not in homework) and ("homework_name" not in homework):
        logging.error("Отсутствует ожидаемый ключ")
        raise StatusError
    homework_status = homework.get("status")
    homework_name = homework.get("homework_name")
    if homework_status not in HOMEWORK_STATUSES:
        logging.error("Недокументированный статус домашней работы")
        raise StatusError
    return (
        f'Изменился статус проверки работы "'
        f'{homework_name}". '
        f"{HOMEWORK_STATUSES.get(homework_status)}"
    )


def check_tokens():
    """Проверяет доступность необходимых переменных окружения.
    Если отсутствует хотя бы одна переменная окружения — функция должна
    вернуть False, иначе — True.
    """
    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        logging.critical(
            "Отсутствует одна из обязательных переменных окружения"
        )
        return False
    return True


def message_sendler(bot, message, saved_message):
    """Отправляет сообщение, если оно изменилось.
    Если сообщение было отправлено ранее, повторной отправки не происходит,
    иначе сообщение отправляется и возвращается для сохранения в переменную.
    """
    if not message == saved_message:
        send_message(bot, message)
    else:
        logging.debug("Статус не изменился")
    time.sleep(RETRY_TIME)
    return message


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    saved_message = None
    try:
        while check_tokens():
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if len(homeworks) == 0:
                    raise EmptyList
                message = parse_status(homeworks[0])
                saved_message = message_sendler(bot, message, saved_message)
                current_timestamp = response.get("current_date")
            except (
                ServerError,
                StatusError,
                ResponseError,
                EmptyList,
                MessageError
            ) as err:
                saved_message = message_sendler(
                    bot, err.message, saved_message
                )
                continue
    except KeyboardInterrupt:
        print(" Остановка бота")


if __name__ == "__main__":
    main()
