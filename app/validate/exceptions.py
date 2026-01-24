'''Исключения валидации и ограничений.'''

class ObjectInUseError(RuntimeError):
    '''Ошибка удаления объекта с активными ссылками.'''


class NotFoundError(RuntimeError):
    pass
