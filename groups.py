import json
import logging
import os

from telegram import Update
from telegram.ext import CallbackContext

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

JSON_FILE = "groups.json"

# Получение айди группы из ссылки
def extract_telegram_id(url: str):
    try:
        parts = url.split("/#")
        if len(parts) > 1 and parts[1].startswith("-"):
            return int(parts[1])
    except Exception:
        pass
    return None

# Функция загрузки списка групп
def load_groups():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return []


# Функция сохранения списка групп
def save_groups(groups):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=4)


# Добавление группы в JSON
def add_group(chat_id):
    groups = load_groups()
    if chat_id not in groups:
        groups.append(chat_id)
        save_groups(groups)
        logging.info(f"✅ Группа {chat_id} добавлена в список рассылки.")
    else:
        logging.info(f"ℹ️ Группа {chat_id} уже в списке.")


# Удаление группы
def remove_group(chat_id):
    groups = load_groups()
    if chat_id in groups:
        groups.remove(chat_id)
        save_groups(groups)
        logging.info(f"❌ Группа {chat_id} удалена из списка.")

# Обновление ID группы в JSON
def update_group_id(old_chat_id, new_chat_id):
    groups = load_groups()

    if old_chat_id in groups:
        groups.remove(old_chat_id)
        groups.append(new_chat_id)
        save_groups(groups)
        logging.info(f"✅ Обновили ID группы: {old_chat_id} → {new_chat_id}")

# Обработка события "бот присоединился к группе"
def bot_joined(update: Update, context: CallbackContext):
    new_members = update.message.new_chat_members
    chat = update.message.chat

    for member in new_members:
        if member.is_bot and member.id == context.bot.id:
            add_group(chat.id)
            break

# Обработка события "бот покинул группу"
def bot_left(update: Update, context: CallbackContext):
    left_member = update.message.left_chat_member
    chat = update.message.chat

    if left_member and left_member.is_bot and left_member.id == context.bot.id:
        remove_group(chat.id)

# Миграция группы (из обычной в супергруппу)
def handle_migration(update: Update, context: CallbackContext):
    if update.message.migrate_to_chat_id:
        old_chat_id = update.message.chat_id
        new_chat_id = update.message.migrate_to_chat_id

        logging.info(f"🔄 Группа {old_chat_id} мигрировала в супергруппу {new_chat_id}")

        # Обновляем ID группы в базе или JSON
        update_group_id(old_chat_id, new_chat_id)
