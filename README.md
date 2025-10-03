# 🤖 Investment Risk Profile Bot

Telegram-бот для подбора инвестиционного продукта по риск-профилю клиента.
⚠️ Важно: Бот носит образовательный характер и не является индивидуальной инвестиционной рекомендацией.

## 🚀 Запуск локально

1. Установи Python 3.11+
2. Создай окружение и установи зависимости:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3. Укажи токен (в файле .env или переменной окружения):
```
BOT_TOKEN=твой_токен
```
4. Запусти:
```bash
python app/bot.py
```

## ☁️ Запуск на Railway

1. Залей проект в GitHub
2. Подключи репозиторий к Railway
3. В Variables добавь BOT_TOKEN
4. Укажи команды:
   - Build: `pip install -r requirements.txt`
   - Start: `python app/bot.py`
