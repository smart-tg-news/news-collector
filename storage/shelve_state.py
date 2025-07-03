import shelve
from contextlib import contextmanager
from typing import Any


@contextmanager
def open_state(path: str):
    db = shelve.open(path)
    try:
        yield db
    finally:
        db.close()


def get_value(path: str, key: str, default: Any = None) -> Any:
    with open_state(path) as db:
        return db.get(key, default)


def set_value(path: str, key: str, value: Any) -> None:
    with open_state(path) as db:
        db[key] = value
