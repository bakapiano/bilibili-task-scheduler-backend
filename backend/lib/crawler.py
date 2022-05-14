import asyncio
import logging

import qrcode

import aiohttp
from qrcode.image.pil import PilImage


async def get_login_qrcode_data() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://passport.bilibili.com/qrcode/getLoginUrl") as response:
            data: dict = await response.json()
            return data


async def gen_login_qrcode() -> PilImage:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://passport.bilibili.com/qrcode/getLoginUrl") as response:
            data: dict = await response.json()
            url: str = data.get("data").get("url")
            image: PilImage = qrcode.make(url)
            print(data)
            return image


async def get_scan_info(oauth_key: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post("https://passport.bilibili.com/qrcode/getLoginInfo",
                                data={'oauthKey': oauth_key}) as response:
            result: dict = await response.json()
            return result


async def test_cookie_jar(cookie_jar: aiohttp.CookieJar) -> bool:
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        async with session.get("https://api.bilibili.com/x/member/medal/my/info") as response:
            result: dict = await response.json()
            return result.get("code") == 0


async def send_live_room_danmuku(
        # 由位置参数传入
        task_info,
        cookie_jar: aiohttp.CookieJar,
        message: str,
        # 由 kwargs 传入
        room_id: str,
        # 接住用不到的参数
        *args,
        **kwargs,
):
    bili_jct: str = cookie_jar._cookies.get("bilibili.com").get("bili_jct").value
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        async with session.post("https://api.live.bilibili.com/msg/send", data={
            "bubble": 0,
            "msg": message,
            "color": 16777215,
            "mode": 1,
            "fontsize": 25,
            "rnd": 1652339204,
            "roomid": room_id,
            "csrf": bili_jct,
            "csrf_token": bili_jct,
        }) as response:
            result = await response.json()
            logging.info(f"[直播间独轮车] room_id:{room_id} message:{message}")
            logging.info(result)
            if result.get("code") != 0:
                raise Exception("弹幕发送失败")
            return result


async def add_comment(
        # 由位置参数传入
        task_info,
        cookie_jar: aiohttp.CookieJar,
        message: str,
        # 由 kwargs 传入
        comment_id: str,
        comment_type: int,
        # 接住用不到的参数
        *args,
        **kwargs,
):
    bili_jct: str = cookie_jar._cookies.get("bilibili.com").get("bili_jct").value
    url = "https://api.bilibili.com/x/v2/reply/add"
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        async with session.post(url=url, data={
            "oid": comment_id,
            "type": comment_type,
            "message": message,
            "plat": 1,
            "ordering": "heat",
            "jsonp": "jsonp",
            "csrf": bili_jct,
        }) as response:
            result: dict = await response.json()
            logging.info(f"[评论区独轮车] comment_id:{comment_id} comment_type:{comment_type} message:{message}")
            logging.info(result)
            if result.get("code") != 0:
                raise Exception("评论发送失败")


# 可以在前端完成
# async def get_comment_id_by_dynamic_id(dynamic_id: str):
#     url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail"
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url=url, params={'id': dynamic_id}) as response:
#             result: dict = await response.json()
#             if result.get("code") == 0:
#                 return result.get("data").get("item").get("basic").get("comment_id_str")
#             else:
#                 raise Exception("无效动态id")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # loop.run_until_complete(asyncio.wait([gen_login_qr_code()]))
