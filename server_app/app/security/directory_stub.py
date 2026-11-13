"""Заглушка корпоративного каталога Active Directory (UC-1, шаг 3).

В реальном развертывании проверка учетных данных выполняется через LDAP-запрос
к контроллеру домена ООО «Санта Ритейл». Для лабораторного контура используется
локальный справочник учетных записей с ролями пользователей.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.core.enums import Role
from app.core.errors import NotAuthenticatedError

_USERS_FILE = Path(__file__).with_name("users.json")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DirectoryStub:
    """Проверка учетных данных пользователя и выдача его роли."""

    def __init__(self, users: dict[str, dict] | None = None) -> None:
        self._users = users or json.loads(_USERS_FILE.read_text(encoding="utf-8"))

    def authenticate(self, login: str, password: str) -> tuple[str, str]:
        """Возвращает пару (login, role) или возбуждает NotAuthenticatedError."""
        record = self._users.get(login)
        if record is None or record["password_hash"] != _sha256(password):
            raise NotAuthenticatedError("Неверное имя пользователя или пароль")
        return login, record["role"]

    def role_of(self, login: str) -> str:
        record = self._users.get(login)
        if record is None:
            raise NotAuthenticatedError()
        return record["role"]
