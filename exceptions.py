class ServerError(Exception):
    """Сервер недоступен."""

    pass


class StatusCodeError(Exception):
    """Не верный код возврата."""

    pass


class ServiceDenaied(Exception):
    """Отказ в обслуживании."""

    pass
