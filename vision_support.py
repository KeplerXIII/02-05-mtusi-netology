"""Анализ изображений через Vision API (OpenAI-совместимый формат, base64)."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import time
from pathlib import Path

from openai import APIError, OpenAI

DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
RETRIES = 3

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

VISION_SYSTEM = (
    "Ты помощник техподдержки CloudBox. Анализируй изображения на русском языке: "
    "опиши содержимое, прочитай видимый текст, отметь ошибки на скриншотах. "
    "Если вопрос про CloudBox — дай практические шаги по хранилищу."
)

logger = logging.getLogger(__name__)


class VisionError(Exception):
    """Ошибка пайплайна анализа изображения."""


def load_env(env_path: Path | None = None) -> None:
    path = env_path or Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def make_vision_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise VisionError(
            "OPENAI_API_KEY не задан. Добавьте ключ в .env (см. .env.example)."
        )
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE)
    return OpenAI(api_key=api_key, base_url=base_url)


def resolve_image_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_file():
        raise VisionError(f"Файл не найден: {path}")
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise VisionError(
            f"Неподдерживаемый формат «{ext or '(без расширения)'}». "
            f"Допустимо: {supported}"
        )
    return path.resolve()


def encode_image_base64(path: Path) -> tuple[str, str]:
    """Читает файл и возвращает (base64, media_type)."""
    data = path.read_bytes()
    if not data:
        raise VisionError(f"Файл пустой: {path}")

    media_type, _ = mimetypes.guess_type(path.name)
    if not media_type or not media_type.startswith("image/"):
        media_type = f"image/{path.suffix.lstrip('.').lower()}"
        if media_type == "image/jpg":
            media_type = "image/jpeg"

    encoded = base64.standard_b64encode(data).decode("ascii")
    return encoded, media_type


def build_vision_messages(
    image_b64: str,
    media_type: str,
    question: str,
) -> list[dict]:
    data_url = f"data:{media_type};base64,{image_b64}"
    return [
        {"role": "system", "content": VISION_SYSTEM},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": data_url},
                },
                {"type": "text", "text": question},
            ],
        },
    ]


def call_vision_api(
    client: OpenAI,
    messages: list[dict],
    *,
    model: str | None = None,
) -> str:
    model_name = model or os.getenv("OPENAI_VISION_MODEL", DEFAULT_MODEL)
    last_error: Exception | None = None

    for attempt in range(1, RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            if not content:
                raise VisionError("API вернул пустой ответ.")
            return content.strip()
        except VisionError:
            raise
        except APIError as e:
            last_error = e
            logger.warning("Vision API attempt %s failed: %s", attempt, e)
            if attempt < RETRIES:
                time.sleep(attempt)
        except Exception as e:
            last_error = e
            logger.warning("Vision API attempt %s failed: %s", attempt, e)
            if attempt < RETRIES:
                time.sleep(attempt)

    raise VisionError(f"Ошибка Vision API: {last_error}")


def analyze_image(
    client: OpenAI,
    path_str: str,
    question: str,
) -> str:
    """Полный пайплайн: путь → base64 → Vision API → текст."""
    path = resolve_image_path(path_str)
    image_b64, media_type = encode_image_base64(path)
    messages = build_vision_messages(image_b64, media_type, question)
    return call_vision_api(client, messages)
