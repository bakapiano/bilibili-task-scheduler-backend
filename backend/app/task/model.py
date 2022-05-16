from sqlalchemy import Column, String, Integer, Text, DateTime, Table, Enum

from backend.app.db import metadata

from backend.celery.tasks import TaskType, TASK_TYPE_VALUES

tasks = Table(
    "BiliTask",
    metadata,
    Column("id", Integer, primary_key=True, index=True, unique=True, autoincrement=True),
    Column("user_id", String(32), nullable=False, index=True),
    # Column("cookies", Text, nullable=False),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("end_time", DateTime(timezone=True), nullable=False),
    Column("interval", Integer, nullable=False),
    Column("bullets", String(1024), nullable=False),
    Column("url", String(256), nullable=False),
    Column("key", String(32), nullable=False),
    Column("status", Enum("等待中", "执行中", "已完成", "已取消", name="task_status"), nullable=False),
    Column("task_type", Enum(*TASK_TYPE_VALUES, name="task_type"), nullable=False),
    Column("success_count", Integer),
    Column("total_count", Integer),
)
