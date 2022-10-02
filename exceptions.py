class ServerError(Exception):
    """Сервер c API недоступен."""

    message = "Сервер c API недоступен"


class ServiceDenaied(Exception):
    """Отказ в обслуживании."""

    message = "Отказ в обслуживании"