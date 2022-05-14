from enum import Enum

from backend.lib.crawler import add_comment, send_live_room_danmuku


class TaskType(str, Enum):
    live = "直播"
    comment = "评论"


TASK_DICT = {
    TaskType.comment: add_comment,
    TaskType.live: send_live_room_danmuku,
}

TASK_TYPE_VALUES = [i.value for i in TaskType.__members__.values()]
print(TASK_TYPE_VALUES)
