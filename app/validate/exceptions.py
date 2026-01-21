class ObjectInUseError(RuntimeError):
    """Нельзя удалить объект: на него есть ссылки (покупки/продукты и т.п.)."""


class NotFoundError(RuntimeError):
    pass
