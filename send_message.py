import argparse
import logging

import phonenumbers
import telegram
from environs import Env
from phonenumbers.phonenumberutil import NumberParseException

from groups import load_groups, extract_telegram_id
from main import load_database, rewrite_file


def parse_console_arguments():
    parser = argparse.ArgumentParser(description='Отправка сообщения в телеграмм бот по номеру телефона.')
    parser.add_argument('phone_number', help='Конечная страница', type=str)
    parser.add_argument('message', help='Начальная страница', type=str)
    return parser


def send_message(chat_id, message_text, phone_number, database):
    try:
        if not chat_id:
            print(f'Пользователь с таким телефонным номером не подписался.')
            return

        bot = telegram.Bot(token=TELEGRAM_TOKEN)

        if len(message_text) > MAX_MESSAGE_LENGTH:
            messages = [message_text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message_text), MAX_MESSAGE_LENGTH)]
            for message in messages:
                bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            return

        bot.send_message(chat_id=chat_id, text=args.message, parse_mode='HTML')

        print(f'Отправлено сообщение на номер {phone_number}. Текст сообщения {args.message}.')
    except telegram.error.Unauthorized:
        print(f'Пользователь с телефонным номером {phone_number} отписался. Удаляю его из базы.')
        database['chats'].pop(phone_number, None)
        rewrite_file(database)


# Команда для рассылки во все группы
def send_all_groups(message_text, groups):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    for chat_id in groups:
        send_message_to_group(message_text, bot, chat_id)


# Команда отправки сообщения в группу
def send_message_to_group(message_text, bot, chat_id):
    try:
        admins = bot.get_chat_administrators(chat_id)

        if not any(admin.user.id == bot.id for admin in admins):
            return

        if len(message_text) > MAX_MESSAGE_LENGTH:
            messages = [message_text[i:i + MAX_MESSAGE_LENGTH] for i in
                        range(0, len(message_text), MAX_MESSAGE_LENGTH)]
            for message in messages:
                bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            return

        bot.send_message(chat_id=chat_id, text=args.message, parse_mode='HTML')

        print(f"📩 Отправлено сообщение в {chat_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки в {chat_id}: {e}")


# Отправка сообщения в определенную группу
def send_to_current_group(message_text, chat_id, groups):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    dop_chat_id = int(str(chat_id).replace('-', '-100'))
    dop2_chat_id = int(str(chat_id).replace('-100', '-'))

    if chat_id in groups:
        send_message_to_group(message_text=message_text, bot=bot, chat_id=chat_id)
        return

    if dop_chat_id in groups:
        send_message_to_group(message_text=message_text, bot=bot, chat_id=dop_chat_id)
        return

    if dop2_chat_id in groups:
        send_message_to_group(message_text=message_text, bot=bot, chat_id=dop2_chat_id)
        return

if __name__ == '__main__':
    args = parse_console_arguments().parse_args()

    message_text = args.message

    env = Env()
    env.read_env()
    TELEGRAM_TOKEN = env('TELEGRAM_TOKEN')
    MAX_MESSAGE_LENGTH = 4095

    database = load_database()
    groups = load_groups()

    try:
        if args.phone_number == 'all':
            for phone_id_pair in database['chats'].copy().items():
                send_message(phone_id_pair[1], message_text, phone_id_pair[0], database)

        elif args.phone_number == 'all_groups_tg':
            send_all_groups(message_text=message_text, groups=groups)

        elif 'https://web.telegram.org' in args.phone_number:
            chat_id = extract_telegram_id(args.phone_number)

            send_to_current_group(message_text=message_text, chat_id=chat_id, groups=groups)

        else:
            phone_number = phonenumbers.parse(args.phone_number, 'RU')
            phone_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

            chat_id = database['chats'].get(phone_number)
            send_message(chat_id, message_text, phone_number, database)

    except NumberParseException as e:
        if e.error_type == 0:
            print(f'Некорректный код страны.')
        elif e.error_type == 1:
            print(f'Либо вы ввели буквы, либо слишком короткий номер.')
        elif e.error_type == 2 or e.error_type == 3:
            print(f'Слишком короткий номер.')
        elif e.error_type == 4:
            print(f'Слишком длинный номер.')
