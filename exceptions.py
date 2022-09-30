class StatusError(KeyError):
    """Ошибка извлечения статуса проверки."""

    message = "Ошибка извлечения статуса проверки"


class NoDictError(TypeError):
    """В ответе не получен словарь."""

    message = "В ответе не получен словарь"


class ServerError(Exception):
    """Сервер API недоступен."""

    message = "Сервер API недоступен"


class ResponseError(Exception):
    """Ответ API не соответсвует ожидаемому."""

    message = "Ответ API не соответсвует ожидаемому"


class EmptyList(Exception):
    """Нет работ на проверке после указанной даты."""

    message = "Работа не проверяется"


class MessageError(Exception):
    """Не удалось отправить сообщение."""

    message = "Не удалось отправить сообщение"
