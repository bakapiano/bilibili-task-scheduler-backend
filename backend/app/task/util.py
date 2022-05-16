import asyncio
import re
from urllib import parse

import aiohttp
from fastapi import HTTPException
from starlette import status

from backend.celery.tasks import TaskType

table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'  # 码表
tr = {}  # 反查码表
# 初始化反查码表
for i in range(58):
    tr[table[i]] = i
s = [11, 10, 3, 8, 4, 6]  # 位置编码表
xor = 177451812  # 固定异或值
add = 8728348608  # 固定加法值


def bv2av(x):
    r = 0
    for i in range(6):
        r += tr[x[s[i]]] * 58 ** i
    return (r - add) ^ xor


def av2bv(x):
    x = (x ^ xor) + add
    r = list('BV1  4 1 7  ')
    for i in range(6):
        r[s[i]] = table[x // 58 ** i % 58]
    return ''.join(r)


async def parse_url(url: str) -> dict:
    parse_result = parse.urlparse(url)

    async with aiohttp.ClientSession() as session:

        # 直播间独轮车
        if "live.bilibili.com" == parse_result.netloc:
            # room_id = parse_result.path.split("/")[-1]

            async with session.get(url) as response:
                text = await response.text()

                pattern = re.compile(r'"room_id":([0-9]*?),')
                room_id = pattern.findall(text)[0]

                pattern = re.compile(r'"title":"(.*?)","cover":')
                live_room_name = pattern.findall(text)[0]

                pattern = re.compile(r'{"base_info":{"uname":"(.*?)","face"')
                live_room_owner = pattern.findall(text)[0]
                title = f"{live_room_owner}-{live_room_name}"

            return {
                "title": title,
                "key": room_id,
                "task_type": TaskType.live,
                "room_id": room_id,
            }

        # 视频评论区
        elif (parse_result.netloc == "www.bilibili.com" or parse_result.netloc == "m.bilibili.com") \
                and "video" in parse_result.path:
            video_bv = parse_result.path.split("/")[-1]

            async with session.get(url) as response:
                text = await response.text()
                pattern = re.compile(r'<title data-vue-meta="true">(.*?)</title>')
                video_name = pattern.findall(text)[0]
                pattern = re.compile(r'itemprop="author" name="author" content="(.*?)">')
                video_owner = pattern.findall(text)[0]
                title = "-".join([video_owner, video_name])

            return {
                "title": title,
                "key": video_bv,
                "task_type": TaskType.comment,
                "comment_type": 1,
                "comment_id": bv2av(video_bv),
            }

        # 动态评论区 PC
        elif parse_result.netloc == "t.bilibili.com" or \
                (parse_result.netloc == "m.bilibili.com" and "dynamic" in parse_result.path):
            dynamic_id = parse_result.path.split("/")[-1] if "dynamic" in parse_result.path else parse_result.path[1:]

            async with session.get("https://api.bilibili.com/x/polymer/web-dynamic/v1/detail", params={
                "timezone_offset": -480,
                "id": dynamic_id,
            }) as response:
                data: dict = await response.json()
                if data.get("code") != 0:
                    raise HTTPException(detail="动态不存在", status_code=status.HTTP_404_NOT_FOUND)
                comment_id = data.get("data").get("item").get("basic").get("comment_id_str")
                comment_type = data.get("data").get("item").get("basic").get("comment_type")
                title = data['data']['item']['modules']['module_author']['name'] + "的动态"

            return {
                "title": title,
                "key": dynamic_id,
                "task_type": TaskType.comment,
                "comment_type": comment_type,
                "comment_id": comment_id,
            }

        raise HTTPException(detail="不支持的链接", status_code=status.HTTP_400_BAD_REQUEST)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(asyncio.wait([
        parse_url("https://t.bilibili.com/659686296425332756?spm_id_from=444.41.0.0"),
        parse_url("https://t.bilibili.com/659685094074613792?spm_id_from=444.41.list.card_time.click"),
        parse_url("https://t.bilibili.com/659681211163082867?spm_id_from=444.41.list.card_time.click"),
        parse_url("https://t.bilibili.com/658971394809266198?spm_id_from=333.999.list.card_time.click"),
        # parse_url("https://www.bilibili.com/video/BV19Z4y1k7P7?spm_id_from=333.999.0.0"),
        parse_url("https://www.bilibili.com/video/BV1kL411K7wV?spm_id_from=333.999.0.0"),
        parse_url("https://live.bilibili.com/22625025?broadcast_type=0&is_room_feed=1&spm_id_from=333.999.0.0"),
        parse_url("https://live.bilibili.com/605?hotRank=0&session_id=02165bef96d7dee1195133b06d8d4d08_8DE40BB8-22DD-436F-B3B7-6F858841A7B5&visit_id=409t8kymixy0"),
        parse_url("https://live.bilibili.com/10413051?hotRank=0&session_id=0597eddb708715b3c356498c0cc6ea88_1F4BF8DE-9B68-4C5C-8473-C51C84344EFE&visit_id=16h6692kmfsw"),
    ]))
    print(result)
