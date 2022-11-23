import json
import logging
import os
from typing import Optional

import redis
from celery import Celery
from fastapi import FastAPI
from prettyconf import config
from pydantic import BaseModel

DEBUG = config("DEBUG", cast=config.boolean, default=False)
CHANNEL = config("CHANNEL", default="test")
REDIS_HOST = config("REDIS_HOST", default="redis")

CELERY_BROKER_URL = os.getenv("REDISSERVER", "redis://redis:6379")
CELERY_RESULT_BACKEND = os.getenv("REDISSERVER", "redis://redis:6379")

celery = Celery("celery", backend=CELERY_BROKER_URL, broker=CELERY_RESULT_BACKEND)


class Item(BaseModel):
    name: str


def publish(message):
    while True:  # note: limit this to x attempts, not a good idea to try indefinitely
        global r
        try:
            # if(random.randint(0,9) < 3):
            #     raise redis.ConnectionError("Test Connection Error")
            rcvd = r.publish(CHANNEL, message)
            if rcvd >0:
                break
        except redis.ConnectionError as e:
            logging.error(e)
            logging.error("Will attempt to retry")
        except Exception as e:
            logging.error(e)
            logging.error("Other exception")


app = FastAPI()
r = redis.Redis(host=REDIS_HOST)


@app.get("/")
async def root():
    return "OK"


@app.post("/messaging/send")
async def send_message(
    message: Optional[str] = ''
    ):
    if message != '':
        publish(message)
    else:
        publish("test message")
    return {"status": "succes"}


@app.post("/task_hello_world/")
async def create_item(item: Item):
    task_name = "hello.task"
    task = celery.send_task(task_name, args=[item.name])
    return dict(id=task.id, url='localhost:5000/check_task/{}'.format(task.id))


@app.get("/check_task/{id}")
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

