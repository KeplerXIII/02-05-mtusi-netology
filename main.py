#!/usr/bin/env python3
"""ИИ-помощник техподдержки CloudBox (ДЗ 2.5)."""

import logging
import os
import time
from collections import deque
from pathlib import Path

from openai import OpenAI

DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

# --- РРФО: system prompt (Б2.2) ---
SYSTEM_PROMPT = """Роль: ты помощник техподдержки облачного хранилища CloudBox.
Регламент: отвечай вежливо, по делу, на русском языке.
Формат: короткий ответ, 2–4 предложения; при необходимости — нумерованные шаги.
Ограничения: отвечай ТОЛЬКО по теме CloudBox (тарифы, загрузка файлов, синхронизация, оплата, аккаунт). На посторонние темы отвечай: «Я помогаю только по сервису CloudBox. Задайте вопрос о хранилище.»

Примеры:
Пользователь: Сколько места в бесплатном тарифе?
Ассистент: В бесплатном тарифе CloudBox доступно 5 ГБ. Для большего объёма подключите тариф «Стандарт» (100 ГБ) или «Про» (1 ТБ) в разделе «Тарифы» в личном кабинете.

Пользователь: Файлы не синхронизируются между телефоном и компьютером
Ассистент: Проверьте: 1) установлено ли приложение CloudBox на обоих устройствах; 2) включена ли синхронизация в настройках; 3) есть ли интернет. Если проблема остаётся — выйдите из аккаунта и войдите снова.

Пользователь: Какая погода в Москве?
Ассистент: Я помогаю только по сервису CloudBox. Задайте вопрос о хранилище.

Пользователь: Как отменить подписку?
Ассистент: Откройте личный кабинет → «Подписка» → «Отменить автопродление». Доступ к платным функциям сохранится до конца оплаченного периода.
"""

FALLBACK = (
    "Сервис временно недоступен. Попробуйте позже или напишите на support@cloudbox.ru"
)
ESCALATION = "Передаю вопрос специалисту. Ожидайте ответ в течение 24 часов."

MAX_HISTORY = 10
RETRIES = 3

logging.basicConfig(
    filename="support.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)

cache: dict[str, str] = {}
stats = {"hits": 0, "misses": 0, "total": 0}
history: deque = deque(maxlen=MAX_HISTORY)


def classify(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("жалоб", "обман", "верните", "плохо", "ужас", "безобраз")):
        return "жалоба"
    if any(w in t for w in ("не работ", "ошибк", "не загруж", "не открыв", "сломал", "баг")):
        return "тех. проблема"
    return "FAQ"


def build_messages(user_text: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for role, content in history:
        msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": user_text})
    return msgs


def stream_api(client: OpenAI, messages: list[dict]) -> str:
    for attempt in range(1, RETRIES + 1):
        try:
            stream = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                temperature=0.3,
                stream=True,
            )
            parts: list[str] = []
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
                    parts.append(delta)
            return "".join(parts).strip()
        except Exception as e:
            logging.warning("API attempt %s failed: %s", attempt, e)
            if attempt < RETRIES:
                time.sleep(attempt)
    print(FALLBACK, end="", flush=True)
    return FALLBACK


def answer(client: OpenAI | None, question: str) -> None:
    key = question.strip().lower()
    stats["total"] += 1

    if key in cache:
        stats["hits"] += 1
        logging.info("CACHE HIT: %s", question[:50])
        print(f"\nБот: {cache[key]}")
        return

    stats["misses"] += 1
    category = classify(question)
    logging.info("category=%s q=%s", category, question[:80])

    print("\nБот: ", end="", flush=True)
    if category == "жалоба":
        reply = ESCALATION
        print(reply)
    elif client is None:
        reply = FALLBACK
        print(reply)
    else:
        reply = stream_api(client, build_messages(question))
        if category == "тех. проблема" and "специалист" not in reply.lower():
            extra = f"\n\n{ESCALATION}"
            print(extra, end="", flush=True)
            reply += extra
        print()

    cache[key] = reply
    history.append(("user", question))
    history.append(("assistant", reply))


def show_stats():
    total = stats["total"]
    hits = stats["hits"]
    rate = (hits / total * 100) if total else 0
    print(f"Запросов: {total}")
    print(f"Попаданий в кеш: {hits}")
    print(f"Промахов: {stats['misses']}")
    print(f"Hit rate: {rate:.1f}%")
    print(f"Записей в кеше: {len(cache)}")


def load_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def make_client() -> OpenAI | None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE)


def main():
    load_env()
    client = make_client()
    if not client:
        print("DEEPSEEK_API_KEY не задан — кеш/эскалация, API: fallback.")

    print("CloudBox — техподдержка. Команды: /clear /stats /quit")
    while True:
        try:
            text = input("\nВы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания.")
            break

        if not text:
            continue
        cmd = text.lower()
        if cmd == "/quit":
            print("До свидания.")
            break
        if cmd == "/clear":
            history.clear()
            print("История очищена.")
            continue
        if cmd == "/stats":
            show_stats()
            continue

        answer(client, text)


if __name__ == "__main__":
    main()
