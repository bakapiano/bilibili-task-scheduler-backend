import datetime
from enum import Enum

from pydantic import Field
from pydantic.main import BaseModel

from backend.app.task.const import MIN_INTERVAL_SECONDS
from backend.celery.tasks import TaskType


class TaskStatus(str, Enum):
    schedule = "等待中"
    running = "执行中"
    done = "已完成"
    canceled = "已取消"


class BiliTaskPostSchema(BaseModel):
    # 起始时间
    start_time: datetime.datetime
    # 结束时间
    end_time: datetime.datetime
    # 执行频率, 单位秒
    interval: int = Field(..., ge=MIN_INTERVAL_SECONDS)
    # 弹药库
    bullets: str = Field(..., min_length=1, max_length=1024)
    # 直播间房间 id / 评论区 id
    url: str = Field(..., min_length=1, max_length=256)


class BiliTaskSchema(BiliTaskPostSchema):
    # 任务 id
    id: int
    # 用户 uid
    user_id: str
    # 状态
    status: TaskStatus
    # 任务类型
    task_type: TaskType
    # room_id / comment_id
    key: str = Field(..., min_length=1, max_length=32)
    # 成功次数
    success_count: int
    # 尝试次数
    total_count: int
