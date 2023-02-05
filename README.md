<h1 align="center">Homework bot</h1>

<p align="center"><img src="https://img.shields.io/badge/made%20by-geocrane-green">
</p>

Телеграм-бот для проверки статуса ревью:
    раз в 10 минут опрашивает API сервиса Практикум.Домашка и проверяет статус отправленной на ревью домашней работы;
    при обновлении статуса анализирует ответ API и отправляет пользователю соответствующее уведомление в Telegram;
    логирует свою работу и сообщает о важных проблемах сообщением в Telegram.

## Используется:
+ Python 3.7
+ python-telegram-bot


## Запуск проекта (на примере Linux):
Клонируйте репозиторий:
```
git clone https://github.com/geocrane/homework_bot.git
```
Войдите в склонированный репозиторий.
Для запуска поочередно выполните:
```
python3 -m venv venv

source venv/bin/activate

python3 -m pip install --upgrade pip

pip install -r requirements.txt
```
Запустите выполнение файла `homework.py`

<p></p>
<h3 align="center">developed by: Sergey S. Zhuravlev</h3>