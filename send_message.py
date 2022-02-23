import argparse
import telegram
import redis
import json
import phonenumbers
from environs import Env
from phonenumbers.phonenumberutil import NumberParseException


def parse_console_arguments():
    parser = argparse.ArgumentParser(description='Отправка сообщения в телеграмм бот по номеру телефона.')
    parser.add_argument('phone_number', help='Конечная страница', type=str)
    parser.add_argument('message', help='Начальная страница', type=str)
    return parser


def send_message(chat_id, message_text, phone_number, database, redis_db):
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
        print('sdfsdfsdfsdfsdf', phone_number)
        print(f'Пользователь с телефонным номером {phone_number} отписался. Удаляю его из базы.')
        database['chats'].pop(phone_number, None)
        redis_db.set('data', json.dumps(database))


if __name__ == '__main__':
    args = parse_console_arguments().parse_args()

    message_text = args.message

    env = Env()
    env.read_env()
    TELEGRAM_TOKEN = env('TELEGRAM_TOKEN')
    REDIS_PASSWORD = env('REDIS_PASSWORD')
    REDIS_URL = env('REDIS_URL')
    REDIS_PORT = env('REDIS_PORT')
    MAX_MESSAGE_LENGTH = 4095

    redis_db = redis.Redis(host=REDIS_URL, port=REDIS_PORT, db=0, password=REDIS_PASSWORD)

    database = json.loads(redis_db.get('data'))

    try:
        if args.phone_number == 'all':
            for phone_id_pair in database['chats'].copy().items():
                send_message(phone_id_pair[1], message_text, phone_id_pair[0], database, redis_db)
        else:
            phone_number = phonenumbers.parse(args.phone_number, 'RU')
            phone_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

            chat_id = database['chats'].get(phone_number)
            send_message(chat_id, message_text, phone_number, database, redis_db)

    except NumberParseException as e:
        if e.error_type == 0:
            print(f'Некорректный код страны.')
        elif e.error_type == 1:
            print(f'Либо вы ввели буквы, либо слишком короткий номер.')
        elif e.error_type == 2 or e.error_type == 3:
            print(f'Слишком короткий номер.')
        elif e.error_type == 4:
            print(f'Слишком длинный номер.')
