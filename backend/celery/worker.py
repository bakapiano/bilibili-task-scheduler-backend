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

RUNNING_COUNT_SAVE_INTERVAL = 10
SAVE_COLUMN_NAMES = [
    "total_count",
    "success_count",
]


def increase_value(_dict: dict, col_name: str):
    value = _dict.get(col_name)
    if value is None:
        value = 0
    _dict[col_name] = value + 1


# 保存任务成功/尝试次数，force：是否强制保存
async def save_task_running_count(task_info: BiliTaskSchema, force: bool = False, *args, **kwargs):
    count = kwargs.get("count")
    if count is None:
        count = 0

    if count >= RUNNING_COUNT_SAVE_INTERVAL or force:
        async with Database(DATABASE_URL) as database:
            # 获取待更新列的值
            values = {}
            for col in SAVE_COLUMN_NAMES:
                col_value = kwargs.get(col)
                if not (col_value is None):
                    values[col] = col_value
            logging.info(f"Saving count for task {task_info.id}, {values}")
            await database.execute(tasks.update().where(tasks.c.id == task_info.id).values(values))
        return True
    else:
        return False


# 更新任务状态
async def update_task_status(task_info: BiliTaskSchema, status: TaskStatus):
    async with Database(DATABASE_URL) as database:
        await database.execute(tasks.update().where(tasks.c.id == task_info.id).values({"status": status}))


async def run_task(task_info: BiliTaskSchema, *args, **kwargs):
    logging.info(f"{task_info} 开始执行")

    if datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('UTC')) >= task_info.end_time:
        await update_task_status(task_info, TaskStatus.done)
        await save_task_running_count(task_info, True, *args, **kwargs)
        return

    if kwargs.get("first"):
        await update_task_status(task_info, TaskStatus.running)
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
        increase_value(kwargs, "success_count")
    except Exception as e:
        logging.error(e)

    increase_value(kwargs, "count")
    increase_value(kwargs, "total_count")
    saved = await save_task_running_count(task_info, False, *args, **kwargs)
    if saved:
        kwargs['count'] = 0

    eta = datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('UTC')) + datetime.timedelta(
        seconds=task_info.interval)
    if eta < task_info.end_time:
        create_bili_task.apply_async(args=(jsonable_encoder(task_info), *args), kwargs=kwargs, eta=eta)
    else:
        await update_task_status(task_info, TaskStatus.done)
        await save_task_running_count(task_info, True, *args, **kwargs)
        logging.info(f"{task_info} 执行结束")


@celery.task(name="create_task")
def create_bili_task(task_info_json: dict, *args, **kwargs):
    if kwargs.get("first") is None:
        kwargs['first'] = True
    logging.info(f"{task_info_json} {args} {kwargs}")
    asyncio.run(run_task(BiliTaskSchema(**task_info_json), *args, **kwargs))
