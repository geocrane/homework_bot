class ServerError(Exception):
    """Сервер c API недоступен."""


class ServiceDenaied(Exception):
    """Отказ в обслуживании."""


class MessageError(Exception):
    """Не удалось отправить сообщение."""