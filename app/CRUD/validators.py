from datetime import date


def validate_date_not_in_future(date: date) -> None:
    if date is None:
        return date.today()
    if date > date.today():
        raise ValueError('Дата покупки не может быть в будущем.')
    return date


def validate_positive_value(
    value: float,
    field_name: str,
) -> None:
    if value <= 0:
        raise ValueError(
            f'{field_name} не может быть меньше или равной нулю.'
        )
    return value