# ДЗ 2.5: ИИ-помощник техподдержки CloudBox

Стек: **uv** + **DeepSeek API** (текст) + **OpenAI Vision API** (изображения).

## Запуск

```bash
# ключи в .env (см. .env.example)
uv sync
uv run python main.py
```

## Команды (main.py)

- `/clear` — очистить историю (10 сообщений)
- `/stats` — hit rate кеша
- `/image <путь> [вопрос]` — анализ изображения (base64 → Vision API)
- `/quit` — выход

## Vision: отдельный скрипт

```bash
# интерактивно
uv run python vision.py

# один файл
uv run python vision.py demo_images/screenshot.png "Есть ли ошибка на экране?"

# демо на трёх типах: фото, скриншот, график
uv run python scripts/make_demo_images.py
uv run python vision.py --demo
```

### Пайплайн

1. Путь к файлу от пользователя
2. Проверка существования и формата (jpg, png, gif, webp)
3. Кодирование в base64 → `data:image/...;base64,...`
4. Запрос в Vision API → текстовое описание / ответ

### Ошибки

- файл не найден
- неподдерживаемый формат
- сбой API (повторы, понятное сообщение)

Логи: `vision.log`, `support.log`.

## Переменные

| Переменная | Назначение |
|------------|------------|
| `DEEPSEEK_API_KEY` | Текстовый чат (main.py) |
| `OPENAI_API_KEY` | Анализ изображений |
| `OPENAI_BASE_URL` | Опционально, совместимый endpoint |
| `OPENAI_VISION_MODEL` | По умолчанию `gpt-4o-mini` |

Файл `.env` не коммитить.
