"""Реестр версий моделей (ЛР8: сохранение с номером версии и меткой времени).

Обеспечивает воспроизводимость результатов и откат к предыдущей версии
при обнаружении деградации точности (ЛР8, пояснение к алгоритму обучения).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib


@dataclass
class ModelMeta:
    version: str
    trained_at: str
    category: str | None
    mape: float
    wape: float
    iterations: int


class ModelRegistry:
    """Каталог моделей на диске: model-{version}.joblib + registry.json."""

    def __init__(self, registry_dir: str | Path) -> None:
        self._dir = Path(registry_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self._dir / "registry.json"

    def _read_all(self) -> list[dict]:
        if self._meta_path.exists():
            return json.loads(self._meta_path.read_text(encoding="utf-8"))
        return []

    def _write_all(self, items: list[dict]) -> None:
        self._meta_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def save(self, model, meta: ModelMeta) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        filename = f"model-{stamp}.joblib"
        joblib.dump(model, self._dir / filename)
        items = self._read_all()
        items.append({**asdict(meta), "file": filename})
        self._write_all(items)

    def load_latest(self):
        items = self._read_all()
        if not items:
            return None
        latest = items[-1]
        return joblib.load(self._dir / latest["file"])

    def latest_meta(self) -> ModelMeta | None:
        items = self._read_all()
        if not items:
            return None
        latest = items[-1]
        latest.pop("file", None)
        return ModelMeta(**latest)

    def list_meta(self) -> list[ModelMeta]:
        items = self._read_all()
        items.reverse()
        return [
            ModelMeta(**{k: v for k, v in item.items() if k != "file"})
            for item in items
        ]
