from environs import Env
import redis
import json


if __name__ == '__main__':
    env = Env()
    env.read_env()
    TELEGRAM_TOKEN = env('TELEGRAM_TOKEN')
    REDIS_PASSWORD = env('REDIS_PASSWORD')
    REDIS_URL = env('REDIS_URL')

    current_state = 'start'

    redis_db = redis.Redis(host=REDIS_URL, port=12076, db=0, password=REDIS_PASSWORD)

    database = json.loads(redis_db.get('data'))

    with open('backup.json', 'w') as file:
        json.dump(database, file, indent=2)
