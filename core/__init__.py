from telebot.async_telebot import AsyncTeleBot

import os
import logging
from datetime import datetime
import gzip
from dotenv import load_dotenv
import yaml
import pymorphy3


current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
current_log_path = os.path.join(os.getcwd(), "logs/latest.log")
new_log_filename = f"log_{current_datetime}.log"
new_log_path = os.path.join(os.getcwd(), f"logs/{new_log_filename}")
log_archive_path = os.path.join(os.getcwd(), f"logs/log_{current_datetime}.gz")

if not os.path.isdir("logs"):
    os.mkdir("logs")

log_dir = os.path.join(os.getcwd(), "logs")

log_files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]

# Отсортируйте список файлов по дате создания
log_files.sort(key=lambda x: os.path.getctime(os.path.join(log_dir, x)))

# Если количество файлов превышает 30, удалите старые файлы
if len(log_files) > 20:
    files_to_delete = log_files[: len(log_files) - 20]
    for file_name in files_to_delete:
        file_path = os.path.join(log_dir, file_name)
        os.remove(file_path)


# Проверяем, существует ли текущий файл логов
if os.path.exists(current_log_path):
    # Переименовываем текущий файл логов
    os.rename(current_log_path, new_log_path)
    with open(new_log_path, "rb") as log:
        with gzip.open(log_archive_path, "wb") as f:
            f.writelines(log)

    # Удаляем файл логов после архивации
    os.remove(new_log_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s\n\n",
    filename="logs/latest.log",
    filemode="w",
)


# Загрузка конфиг файла
config_path = os.path.join(os.getcwd(), "config.yaml")
try:
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"Ошибка при загрузке файла config.yaml: \n{e}")
    logging.critical(f"Ошибка при загрузке файла config.yaml: \n{e}")
    exit()


# Загрузка файла сообщений
messages_path = os.path.join(os.getcwd(), "messages.yaml")
try:
    with open(messages_path, encoding="utf-8") as f:
        messages = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"Ошибка при загрузке файла messages.yaml: \n{e}")
    logging.critical(f"Ошибка при загрузке файла messages.yaml: \n{e}")
    exit()


# Загрузка файла предметов
messages_path = os.path.join(os.getcwd(), "items.yaml")
try:
    with open(messages_path, encoding="utf-8") as f:
        inventory_items = yaml.safe_load(f)
except yaml.YAMLError as e:
    print(f"Ошибка при загрузке файла items.yaml: \n{e}")
    logging.critical(f"Ошибка при загрузке файла items.yaml: \n{e}")
    exit()


morph = pymorphy3.MorphAnalyzer(lang="ru")

from core.database import Base, engine_db


async def init_models():
    async with engine_db.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Инициализация бота
load_dotenv()
if os.getenv('TELEGRAM_TOKEN') is not None:
    bot = AsyncTeleBot(os.getenv("TELEGRAM_TOKEN"))
    logging.info("Бот запущен")
    print("Бот запущен")
else:
    logging.critical("Отсутствует переменная окружения TELEGRAM_TOKEN")
    print("Отсутствует переменная окружения TELEGRAM_TOKEN")
    exit()
