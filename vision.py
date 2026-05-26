#!/usr/bin/env python3
"""CLI: анализ изображений через Vision API."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from vision_support import (
    VisionError,
    analyze_image,
    load_env,
    make_vision_client,
)

DEMO_DIR = Path(__file__).resolve().parent / "demo_images"

DEMO_CASES = [
    (
        "photo.png",
        "Опиши, что изображено на фотографии. Укажи основные объекты и обстановку.",
    ),
    (
        "screenshot.png",
        "Это скриншот интерфейса. Перечисли видимые элементы и текст. "
        "Есть ли сообщения об ошибке?",
    ),
    (
        "chart.png",
        "Опиши данные на графике: подписи осей, значения, тренд.",
    ),
]

logging.basicConfig(
    filename="vision.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)


def print_help() -> None:
    print(
        "Анализ изображений (Vision API, base64)\n"
        "  <путь к файлу> [вопрос]  — описание или ответ на вопрос\n"
        "  /demo                    — три демо: фото, скриншот, график\n"
        "  /quit                    — выход\n"
        f"\nДемо-файлы: {DEMO_DIR}/"
    )


def run_demo(client) -> None:
    if not DEMO_DIR.is_dir():
        print(f"Папка демо не найдена: {DEMO_DIR}")
        print("Создайте изображения: uv run python scripts/make_demo_images.py")
        return

    for filename, question in DEMO_CASES:
        path = DEMO_DIR / filename
        print(f"\n{'=' * 60}")
        print(f"Файл: {path.name} ({question[:50]}…)")
        print("=" * 60)
        try:
            answer = analyze_image(client, str(path), question)
            print(f"\nОтвет:\n{answer}")
            logging.info("demo ok: %s", filename)
        except VisionError as e:
            print(f"\nОшибка: {e}")
            logging.error("demo failed %s: %s", filename, e)


def run_interactive(client) -> None:
    print_help()
    while True:
        try:
            line = input("\nПуть или команда: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания.")
            break

        if not line:
            continue
        cmd = line.lower()
        if cmd in ("/quit", "/q"):
            print("До свидания.")
            break
        if cmd == "/demo":
            run_demo(client)
            continue
        if cmd in ("/help", "/?"):
            print_help()
            continue

        parts = line.split(maxsplit=1)
        image_path = parts[0]
        question = parts[1] if len(parts) > 1 else "Опиши изображение подробно на русском языке."

        try:
            answer = analyze_image(client, image_path, question)
            print(f"\nОтвет:\n{answer}")
            logging.info("ok: %s", image_path)
        except VisionError as e:
            print(f"\nОшибка: {e}")
            logging.error("failed %s: %s", image_path, e)


def main() -> int:
    load_env()
    try:
        client = make_vision_client()
    except VisionError as e:
        print(f"Ошибка: {e}")
        return 1

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        question = (
            " ".join(sys.argv[2:])
            if len(sys.argv) > 2
            else "Опиши изображение подробно на русском языке."
        )
        if image_path in ("--demo", "/demo"):
            run_demo(client)
            return 0
        try:
            answer = analyze_image(client, image_path, question)
            print(answer)
            return 0
        except VisionError as e:
            print(f"Ошибка: {e}", file=sys.stderr)
            return 1

    run_interactive(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
