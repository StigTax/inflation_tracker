from __future__ import annotations

import inspect
import logging
import time
from datetime import date, datetime
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from app.core.constants import DEFAULT_MAXLEN, UNHANDLED

F = TypeVar('F', bound=Callable[..., Any])


def _truncate(
    text: str,
    maxlen: int
) -> str:
    if len(text) <= maxlen:
        return text
    cut = max(0, maxlen-3)
    return text[:cut] + '...'


def _is_model(
    obj: Any
) -> bool:
    mod = getattr(getattr(obj, '__class__', None), '__module__', '')
    return bool(mod) and mod.startswith('app.models')


def _repr_none(value: Any) -> str | object:
    return "None" if value is None else UNHANDLED


def _repr_scalar(value: Any, *, maxlen: int) -> str | object:
    if isinstance(value, (int, float, bool)):
        return repr(value)

    if isinstance(value, str):
        return _truncate(repr(value), maxlen)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return UNHANDLED


def _repr_namespace(
    value: Any,
    *,
    maxlen: int,
    seq_limit: int,
    map_limit: int,
) -> str | object:
    # argparse.Namespace
    if value.__class__.__name__ == "Namespace" and hasattr(value, "__dict__"):
        return _safe_repr(
            vars(value),
            maxlen=maxlen,
            seq_limit=seq_limit,
            map_limit=map_limit,
        )
    return UNHANDLED


def _repr_model(value: Any) -> str | object:
    if _is_model(value):
        obj_id = getattr(value, "id", None)
        cls = value.__class__.__name__
        return f"{cls}(id={obj_id})" if obj_id is not None else cls
    return UNHANDLED


def _repr_mapping(
    value: Any,
    *,
    maxlen: int,
    s_lim: int,
    m_lim: int,
) -> str | object:
    if not isinstance(value, dict):
        return UNHANDLED

    parts: list[str] = []
    for i, (k, v) in enumerate(value.items()):
        if i >= m_lim:
            parts.append(f"...+{len(value) - m_lim} keys")
            break
        parts.append(
            f"{_safe_repr(k, maxlen=40, seq_limit=s_lim, map_limit=m_lim)}: "
            f"{_safe_repr(v, maxlen=80, seq_limit=s_lim, map_limit=m_lim)}"
        )
    return _truncate("{" + ", ".join(parts) + "}", maxlen)


def _repr_sequence(
    value: Any,
    *,
    maxlen: int,
    seq_limit: int,
    map_limit: int,
) -> str | object:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return UNHANDLED

    seq = list(value)
    shown = [
        _safe_repr(v, maxlen=80, seq_limit=seq_limit, map_limit=map_limit)
        for v in seq[:seq_limit]
    ]
    suffix = f", ...+{len(seq) - seq_limit}" if len(seq) > seq_limit else ""

    if isinstance(value, list):
        opener, closer = "[", "]"
    elif isinstance(value, tuple):
        opener, closer = "(", ")"
    else:
        opener, closer = "{", "}"

    return _truncate(opener + ", ".join(shown) + suffix + closer, maxlen)


def _repr_fallback(value: Any, *, maxlen: int) -> str:
    try:
        return _truncate(repr(value), maxlen)
    except Exception:  # pragma: no cover
        return f"<unreprable {type(value).__name__}>"


def _safe_repr(
    value: Any,
    *,
    maxlen: int = DEFAULT_MAXLEN,
    seq_limit: int = 6,
    map_limit: int = 6,
) -> str:
    # Роутер: пробуем обработчики по очереди, первый “поймал” — вернул строку.
    for handler in (
        lambda v: _repr_none(v),
        lambda v: _repr_scalar(v, maxlen=maxlen),
        lambda v: _repr_namespace(
            v,
            maxlen=maxlen,
            seq_limit=seq_limit,
            map_limit=map_limit
        ),
        lambda v: _repr_model(v),
        lambda v: _repr_mapping(
            v,
            maxlen=maxlen,
            s_lim=seq_limit,
            m_lim=map_limit
        ),
        lambda v: _repr_sequence(
            v,
            maxlen=maxlen,
            seq_limit=seq_limit,
            map_limit=map_limit
        ),
    ):
        res = handler(value)
        if res is not UNHANDLED:
            return res  # type: ignore[return-value]

    return _repr_fallback(value, maxlen=maxlen)


def _is_empty_value(val: Any) -> bool:
    return (
        val is None
        or (isinstance(val, str) and val == "")
        or (isinstance(
            val,
            (
                list,
                tuple,
                set,
                frozenset,
                dict
            )
        ) and len(val) == 0)
    )


def _format_call(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    maxlen: int,
    include_defaults: bool,
    skip_none: bool,
    skip_empty: bool,
) -> str:
    try:
        sig = inspect.signature(func)
        bound = sig.bind_partial(*args, **kwargs)

        if include_defaults:
            bound.apply_defaults()

        parts: list[str] = []
        for key, value in bound.arguments.items():
            if key in {'self', 'cls'}:
                continue
            if skip_none and value is None:
                continue

            if skip_empty and _is_empty_value(value):
                continue
            parts.append(f'{key}={_safe_repr(value, maxlen=maxlen)}')

        return ', '.join(parts)
    except Exception:
        return _safe_repr(kwargs, maxlen=maxlen) if kwargs else ''


def logged(
    *,
    name: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    log_args: bool = True,
    log_result: bool = False,
    maxlen: int = DEFAULT_MAXLEN,
    include_defaults: bool = False,
    skip_none: bool = True,
    skip_empty: bool = False,
) -> Callable[[F], F]:
    """Декоратор для логирования вызова функции.

    Пишет: start/ok/error и время выполнения.
    Аргументы/результат форматируются безопасно: с ограничением длины и без
    тяжёлых сериализаций ORM.
    """

    def decorator(func: F) -> F:
        log = logger or logging.getLogger(func.__module__)
        event = name or f'{func.__module__}.{func.__qualname__}'

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            start = time.perf_counter()

            if log_args:
                call = _format_call(
                    func,
                    args,
                    dict(kwargs),
                    maxlen=maxlen,
                    include_defaults=include_defaults,
                    skip_none=skip_none,
                    skip_empty=skip_empty,
                )
                log.log(
                    level,
                    '%s -> start%s',
                    event,
                    f' ({call})' if call else '',
                )
            else:
                log.log(level, '%s -> start', event)

            try:
                result = func(*args, **kwargs)
            except Exception:
                ms = (time.perf_counter() - start) * 1000
                log.exception('%s -> error (%.1fms)', event, ms)
                raise

            ms = (time.perf_counter() - start) * 1000
            if log_result:
                log.log(
                    level,
                    '%s -> ok (%.1fms) result=%s',
                    event,
                    ms,
                    _safe_repr(result, maxlen=maxlen),
                )
            else:
                log.log(level, '%s -> ok (%.1fms)', event, ms)

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
