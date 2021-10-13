import argparse
import telegram
import redis
import json
import phonenumbers
from environs import Env


def parse_console_arguments():
    parser = argparse.ArgumentParser(description='Отправка сообщения в телеграмм бот по номеру телефона.')
    parser.add_argument('phone_number', help='Конечная страница', type=str)
    parser.add_argument('message', help='Начальная страница', type=str)
    return parser


if __name__ == '__main__':
    args = parse_console_arguments().parse_args()

    env = Env()
    env.read_env()
    TELEGRAM_TOKEN = env('TELEGRAM_TOKEN')
    REDIS_PASSWORD = env('REDIS_PASSWORD')
    REDIS_URL = env('REDIS_URL')

    redis_db = redis.Redis(host=REDIS_URL, port=12076, db=0, password=REDIS_PASSWORD)

    database = json.loads(redis_db.get('data'))

    phone_number = phonenumbers.parse(args.phone_number, 'RU')
    phone_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

    chat_id = database['chats'][phone_number]

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=chat_id, text=args.message)

    print(f'Отправлено сообщение на номер {args.phone_number}. Текст сообщения {args.message}.')
