import datetime
import logging
import pickle
from typing import List

import pytz
from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_, func, or_
from starlette import status

from backend.app.auth.depend import get_current_token_data
from backend.app.auth.schema import TokenData
from backend.app.db import database
from backend.app.task.const import MAX_DURATION_SECONDS, MAX_TASKS_PER_USER
from backend.app.task.depend import get_task_by_id
from backend.app.task.model import tasks
from backend.app.task.schema import BiliTaskSchema, TaskStatus, BiliTaskPostSchema
from backend.app.task.util import parse_url
from backend.celery.worker import create_bili_task

task_router = APIRouter()


@task_router.get("/all", response_model=List[BiliTaskSchema])
async def list_all_tasks(
        token_data: TokenData = Depends(get_current_token_data)
):
    return [BiliTaskSchema(**i) for i in
            await database.fetch_all(tasks.select().filter_by(user_id=token_data.user_id))]


@task_router.post("/url/info")
async def get_url_info(url: str = Body(..., min_length=1, embed=True)):
    return await parse_url(url)


@task_router.post("/", response_model=int)
async def create_new_task(
        token_data: TokenData = Depends(get_current_token_data),
        task: BiliTaskPostSchema = Body(...),
):
    if task.start_time < datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('UTC')):
        task.start_time = datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('UTC'))
    if task.end_time <= task.start_time:
        raise HTTPException(detail="结束时间需晚于起始时间！", status_code=status.HTTP_400_BAD_REQUEST)
    duration = task.end_time - task.start_time
    if duration.total_seconds() > MAX_DURATION_SECONDS:
        raise HTTPException(detail=f"持续时间需不能大于{MAX_DURATION_SECONDS}秒！", status_code=status.HTTP_400_BAD_REQUEST)
    if "?" in task.url:
        task.url = task.url.split("?")[0]

    # 检查任务上线
    query = (select(func.count(tasks.c.id)).select_from(tasks).where(and_(tasks.c.user_id == token_data.user_id,
                                                                          or_(tasks.c.status == TaskStatus.schedule,
                                                                              tasks.c.status == TaskStatus.running))))
    count = await database.execute(query)
    logging.info(f"{token_data.user_id} {count}")
    if count >= MAX_TASKS_PER_USER:
        raise HTTPException(detail=f"任务上限 {MAX_TASKS_PER_USER} 个", status_code=status.HTTP_400_BAD_REQUEST)

    args_dict: dict = await parse_url(task.url)

    task_id = await database.execute(tasks.insert().values({
        "user_id": token_data.user_id,
        # "cookies": pickle.dumps(token_data.cookie_jar._cookies, 0).decode(),
        "status": TaskStatus.schedule,
        "task_type": args_dict.get("task_type"),
        **task.dict(),
        "key": args_dict.get("key")
    }).returning(tasks.c.id))

    task_info = BiliTaskSchema(**await database.fetch_one(tasks.select().filter_by(id=task_id)))
    args_dict["cookies"] = pickle.dumps(token_data.cookie_jar._cookies, 0).decode()
    print(args_dict)

    # 添加 Celery 任务
    celery_task_id = create_bili_task.apply_async(args=(jsonable_encoder(task_info),),
                                                  kwargs=args_dict,
                                                  eta=task_info.start_time)

    return task_id


@task_router.get("/{task_id}/")
async def get_task_detail_by_id(task: BiliTaskSchema = Depends(get_task_by_id)):
    return task

# @task_router.put("/{task_id}/")
# async def cancel_task(
#         task: BiliTaskSchema = Depends(get_task_by_id),
# ):
#     if task.status != TaskStatus.running and task.status != TaskStatus.schedule:
#         raise HTTPException(detail=f"无法取消{task.status}的任务", status_code=status.HTTP_400_BAD_REQUEST)
#     await database.execute(tasks.update().where(tasks.c.id == task.id).values(status=TaskStatus.canceled))
# TODO
# redis 标志位
