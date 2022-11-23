import json
import os
import time
import redis
from celery import Celery
from prettyconf import config

CHANNEL = config("CHANNEL", default="test")
REDIS_HOST = config("REDIS_HOST", default="redis")

CELERY_BROKER_URL = os.getenv("REDISSERVER", "redis://redis:6379")
CELERY_RESULT_BACKEND = os.getenv("REDISSERVER", "redis://redis:6379")

celery = Celery("background_job", backend=CELERY_BROKER_URL, broker=CELERY_RESULT_BACKEND)


def main():
    r = redis.Redis(host=REDIS_HOST, decode_responses=True)
    p = r.pubsub(ignore_subscribe_messages=True)
    p.subscribe(CHANNEL)
    while True:
        try:
            message = p.get_message()
            if message:
                print(f"received {message}")
                task_name = "hello.task"
                task = celery.send_task(task_name, args=[message['data']])
                print(f"background_job task sent {task}")
                time.sleep(0.001)
        except redis.ConnectionError:
            # Do reconnection attempts here such as sleeping and retrying
            time.sleep(3)
            p = r.pubsub()
            p.subscribe(CHANNEL)


def check_task(id: str):
    task = celery.AsyncResult(id)
    if task.state == 'SUCCESS':
        response = {
            'status': task.state,
            'result': task.result,
            'task_id': id
        }
    elif task.state == 'FAILURE':
        response = json.loads(task.backend.get(task.backend.get_key_for_task(task.id)).decode('utf-8'))
        del response['children']
        del response['traceback']
    else:
        response = {
            'status': task.state,
            'result': task.info,
            'task_id': id
        }
    return response


if __name__ == "__main__":
    print("Start listening...")
    try:
        main()
    except KeyboardInterrupt:
        pass
