import datetime
import logging
import pickle
import random
import asyncio

import aiohttp
import pytz
from celery import Celery
from databases import Database
from fastapi.encoders import jsonable_encoder

from backend.app.db import DATABASE_URL
from backend.app.task.model import tasks
from backend.app.task.schema import BiliTaskSchema, TaskStatus
from backend.celery.tasks import TASK_DICT
from backend.celery import config

celery = Celery(__name__)
celery.config_from_object(config)

SALT = " -!?.~"
SALT_COUNT = 2


async def run_task(task_info: BiliTaskSchema, *args, **kwargs):
    logging.info(f"{task_info} 开始执行")

    if datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('UTC')) >= task_info.end_time:
        async with Database(DATABASE_URL) as database:
            await database.execute(tasks.update().where(tasks.c.id == task_info.id).values({"status": TaskStatus.done}))
        return

    if kwargs.get("first"):
        async with Database(DATABASE_URL) as database:
            await database.execute(
                tasks.update().where(tasks.c.id == task_info.id).values({"status": TaskStatus.running}))
        kwargs['first'] = False

    cookie_jar = aiohttp.CookieJar()
    cookie_jar._cookies = pickle.loads(str.encode(kwargs.get("cookies")))
    message = random.choice(task_info.bullets.split("\n"))

    # 加盐
    for i in range(SALT_COUNT):
        char = random.choice(SALT)
        index = random.randint(0, len(message))
        message = f"{message[0:index]}{char}{message[index:]}"

    try:
        task_func = TASK_DICT.get(task_info.task_type)
        await task_func(task_info, cookie_jar, message, *args, **kwargs)
    except Exception as e:
        logging.error(e)

    eta = datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('UTC')) + datetime.timedelta(
        seconds=task_info.interval)
    if eta < task_info.end_time:
        create_bili_task.apply_async(args=(jsonable_encoder(task_info), *args), kwargs=kwargs, eta=eta)
    else:
        async with Database(DATABASE_URL) as database:
            await database.execute(tasks.update().where(tasks.c.id == task_info.id).values({"status": TaskStatus.done}))
        logging.info(f"{task_info} 执行结束")


@celery.task(name="create_task")
def create_bili_task(task_info_json: dict, *args, **kwargs):
    if kwargs.get("first") is None:
        kwargs['first'] = True
    logging.info(f"{task_info_json} {args} {kwargs}")
    asyncio.run(run_task(BiliTaskSchema(**task_info_json), *args, **kwargs))
