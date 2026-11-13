"""Журнал уведомлений пользователей (UC-3, UC-9: сообщения о сбоях расчета/экспорта)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Notification:
    login: str
    text: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class NotificationService:
    """Хранит уведомления в памяти процесса (лабораторный контур).

    В промышленной версии уведомления доставляются через почтовый шлюз
    и/или WebSocket-канал интерфейса.
    """

    def __init__(self) -> None:
        self._items: list[Notification] = []

    def notify(self, login: str, text: str) -> None:
        self._items.append(Notification(login=login, text=text))

    def for_user(self, login: str) -> list[Notification]:
        return [n for n in self._items if n.login == login]
