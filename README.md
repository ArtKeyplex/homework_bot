# Homework Bot
Чат-бот Telegram для получения информации о проведенном код-ревью домашнего задания (Telegram API)

Стек технологий
----------
* Python 3.8
* Pytest
* python-telegram-bot
* python-dotenv
* requests

Установка проекта из репозитория
----------

1. Клонировать репозиторий и перейти в него в командной строке:
```bash
git clone git@github.com:ArtKeyplex/homework_bot.git

cd homework_bot
```
2. Cоздать и активировать виртуальное окружение:
```bash
python3 -m venv venv

source venv/bin/activate
```
3. Создать чат-бота в Телеграм 
4. Создать в директории проекта файл .env и поместить туда следующие токены:
```bash
PRAKTIKUM_TOKEN = 'ххххххххх'
TELEGRAM_TOKEN = 'ххххххххххх'
TELEGRAM_CHAT_ID = 'ххххххххххх'
```

5. Открыть файл homework.py и запустить код
```bash
python3 homework.py
```
