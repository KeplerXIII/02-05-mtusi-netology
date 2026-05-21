# ДЗ 2.5: ИИ-помощник техподдержки CloudBox

Стек: **uv** + **DeepSeek API**.

## Запуск

```bash
# ключ в .env (см. .env.example)
uv sync
uv run python main.py
```

## Команды

- `/clear` — очистить историю (10 сообщений)
- `/stats` — hit rate кеша
- `/quit` — выход

## Переменные

`DEEPSEEK_API_KEY` — в файле `.env` (не коммитить).
