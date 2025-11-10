import json

import redis

# Подключаемся к Redis
r = redis.Redis(host="localhost", port=6379, db=0)

# Создаем команду
command = {
    "command": "fetch",
    "chat": "@ru_python",
    "mode": "date",
    "date": "2025-11-07",
}

# Сериализуем в JSON
command_json = json.dumps(command)

# Отправляем команду
r.rpush("tg_commands", command_json)
print(f"Sent command: {command_json}")
