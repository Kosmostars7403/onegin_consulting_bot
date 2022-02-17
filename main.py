from environs import Env
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
import logging
import redis
import json

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Добрый день! Это бот ЮК \"Онегин-Консалтинг\".\n\nОтправьте мне свой номер телефона, а я начну "
             "присылать важные  уведомления по работе. "
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


def change_data(key, chat_id, value):
    database[key][str(chat_id)] = value
    redis_db.set('data', json.dumps(database))


def main():
    updater = Updater(TELEGRAM_TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))

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
    REDIS_PASSWORD = env('REDIS_PASSWORD')
    REDIS_URL = env('REDIS_URL')
    REDIS_PORT = env('REDIS_PORT')

    current_state = 'start'

    redis_db = redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=0, password=REDIS_PASSWORD)
    database = redis_db.get('data') and json.loads(redis_db.get('data')) or {}

    if not database:
        database = {'states': {}, 'chats': {}}
        redis_db.set('data', json.dumps(database))

    main()
