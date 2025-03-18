import json
import logging
import subprocess

import phonenumbers
import telegram
from environs import Env
from phonenumbers.phonenumberutil import NumberParseException
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

from groups import load_groups, bot_joined, bot_left, handle_migration

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Добрый день! Это бот ЮК \"Онегин-Консалтинг\".\n\nОтправьте мне свой номер телефона, а я начну "
             "присылать важные уведомления по работе. "
    )
    change_data('states', update.effective_chat.id, GET_NUMBER)


def parse_text_response(update, context):
    chat_id = str(update.effective_chat.id)
    if database['states'].get(chat_id) == GET_NUMBER:
        handle_phone_number_input(update, context)
    elif database['states'].get(chat_id) == CONFIRM_NUMBER:
        handle_confirmation(update, context)
    elif database['states'].get(chat_id) == NUMBER_SAVED:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Номер уже сохранен, ждите уведомлений.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Не понимаю, чего вы хотите!")


def error(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Случилась какая-то ошибка!")


def handle_phone_number_input(update, context):
    message = update.message.text

    try:
        phone_number = phonenumbers.parse(message, 'RU')
    except NumberParseException as e:
        if e.error_type == 0:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Некорректный код страны.'
            )
        if e.error_type == 1 and len(message) > 1:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Вы вводите буквы, что у вас за номер такой? Повторите ввод!'
            )

        if e.error_type == 1 and len(message) == 1:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Одного символа недостаточно.'
            )

        if e.error_type == 4:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Номер телефона обычно содержит меньше символов, повторите ввод!'
            )
        return

    phone_number_for_save = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)
    phone_number_for_print = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

    if len(phone_number_for_save) < 12:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Номер телефона обычно содержит больше символов, повторите ввод!')
        return

    if len(phone_number_for_save) > 12:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Номер телефона обычно содержит меньше символов, повторите ввод!'
        )
        return

    change_data('chats', phone_number_for_save, update.effective_chat.id)

    custom_keyboard = [['Да, все верно.', 'Нет, повторить ввод.']]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Я немного отформатировал номер, взляните, все верно?\n\n{phone_number_for_print}',
        reply_markup=reply_markup
    )
    change_data('states', update.effective_chat.id, CONFIRM_NUMBER)


def handle_confirmation(update, context):
    message = update.message.text
    reply_markup = telegram.ReplyKeyboardRemove()

    if message == 'Да, все верно.':
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Ваш номер сохранен. Теперь вы начнете получать уведомления в этом чате. Спасибо.',
            reply_markup=reply_markup
        )
        change_data('states', update.effective_chat.id, NUMBER_SAVED)

    elif message == 'Нет, повторить ввод.':
        context.bot.send_message(chat_id=update.effective_chat.id, text='Тогда введите номер повторно.', reply_markup=reply_markup)
        change_data('states', update.effective_chat.id, GET_NUMBER)


def send_message_to_all(update, context):
    if str(update.effective_chat.id) == ADMIN_USER_CHAT_ID:
        subprocess.run(['python3.9', 'send_message.py', 'all', update.message.text[5:]])


def rewrite_file(file_content):
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(file_content, f, indent=2)


def change_data(key, chat_id, value):
    database[key][str(chat_id)] = value
    rewrite_file(database)


def load_database():
    try:
        with open('database.json', 'r', encoding='utf-8') as file:
            db = json.load(file)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        db = {'states': {}, 'chats': {}}
        rewrite_file(db)

    return db


# Команда для рассылки
def send_all_groups(update: Update, context: CallbackContext):
    if str(update.effective_chat.id) != ADMIN_USER_CHAT_ID:
        update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    if not context.args:
        update.message.reply_text("Используйте: /send_all_groups <текст>")
        return

    message_text = " ".join(context.args)
    groups = load_groups()

    if not groups:
        update.message.reply_text("Нет групп для рассылки.")
        return

    count = 0

    for chat_id in groups:
        try:
            bot_id = context.bot.id
            admins = context.bot.get_chat_administrators(chat_id)
            if any(admin.user.id == bot_id for admin in admins):
                context.bot.send_message(chat_id, message_text)
                count += 1
                logging.info(f"📩 Отправлено сообщение в {chat_id}")
        except Exception as e:
            logging.error(f"❌ Ошибка отправки в {chat_id}: {e}")

    update.message.reply_text(f"✅ Сообщение отправлено в {count} групп(ы).")

def main():
    updater = Updater(TELEGRAM_TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("all", send_message_to_all))

    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, bot_joined))
    dispatcher.add_handler(MessageHandler(Filters.status_update.left_chat_member, bot_left))
    dispatcher.add_handler(MessageHandler(Filters.status_update.migrate, handle_migration))

    dispatcher.add_handler(CommandHandler("send_all_groups", send_all_groups, pass_args=True))

    dispatcher.add_handler(MessageHandler(Filters.text, parse_text_response))

    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    START = 'start'
    GET_NUMBER = 'number'
    CONFIRM_NUMBER = 'confirm'
    NUMBER_SAVED = 'saved'

    env = Env()
    env.read_env()
    TELEGRAM_TOKEN = env('TELEGRAM_TOKEN')
    ADMIN_USER_CHAT_ID = env('ADMIN_USER_CHAT_ID')

    current_state = 'start'

    database = load_database()

    main()
