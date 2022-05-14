from fastapi import Depends, Path, HTTPException
from starlette import status

from backend.app.auth.depend import get_current_token_data
from backend.app.auth.schema import TokenData
from backend.app.db import database
from backend.app.task.model import tasks
from backend.app.task.schema import BiliTaskSchema


async def get_task_by_id(
        token_data: TokenData = Depends(get_current_token_data),
        task_id: int = Path(..., ge=0),
) -> BiliTaskSchema:
    task = await database.fetch_one(tasks.select().filter_by(id=task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    task_schema = BiliTaskSchema(**task)
    if task_schema.user_id != token_data.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return task_schema
