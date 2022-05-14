import io
import pickle
from datetime import timedelta

import fastapi
from fastapi import Query, HTTPException, Depends, Body
from starlette import status
from starlette.responses import StreamingResponse

from backend.app.auth.const import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.app.auth.depend import get_current_token_data
from backend.app.auth.schema import Token, TokenData
from backend.app.auth.util import create_access_token
from backend.lib.crawler import *

auth_router = fastapi.APIRouter()


@auth_router.get("/qrcode/info", response_model=dict)
async def get_login_qrcode_info():
    return await get_login_qrcode_data()


@auth_router.get("/qrcode/image")
async def get_login_qrcode_image():
    image = await gen_login_qrcode()
    imgio = io.BytesIO()
    image.save(imgio, 'JPEG')
    imgio.seek(0)
    return StreamingResponse(content=imgio, media_type="image/jpeg")


# @auth_router.post("/info", response_model=dict)
# async def get_qrcode_scan_info(oauth_key: str = Query(..., min_length=32, max_length=32)):
#     return await get_scan_info(oauth_key)


@auth_router.post("/token", response_model=Token)
async def login_with_qrcode_oauth_key(response: fastapi.Response,
                                      oauth_key: str = Body(..., min_length=32, max_length=32, embed=True)):
    cookie_jar = aiohttp.CookieJar()
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        async with session.post("https://passport.bilibili.com/qrcode/getLoginInfo",
                                data={'oauthKey': oauth_key}) as res:
            data: dict = await res.json()
            scan_status: bool = data.get("status")
            if not scan_status:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=data.get("message"))

            url: str = data.get("data").get("url")
            query_params = {}
            for body in url.split("?")[-1].split("&"):
                key, value = body.split("=")
                query_params[key] = value

            user_id = query_params.get("DedeUserID")
            bili_jct = query_params.get("bili_jct")

            # async with session.get(url="https://passport.bilibili.com/web/sso/list",
            #                        params={"biliCSRF": bili_jct}) as res:
            #     data = await res.json()
            #     session.headers.update({"origin": "https://www.bilibili.com"})
            #     session.headers.update({"referer": "https://www.bilibili.com"})
            #     for url in data.get("data").get("sso"):
            #         ticket = url.split("=")[-1]
            #         print(url, ticket)
            #         async with session.post(url=url) as res:
            #             print(await res.json())

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "user_id": user_id,
                "cookies": pickle.dumps(cookie_jar._cookies, 0).decode(),
            },
            expires_delta=access_token_expires
        )
        print(access_token)

        # response.set_cookie(key="token", value=access_token, samesite="none")
        return {"access_token": access_token, "token_type": "bearer"}


@auth_router.get("/me")
async def get_current_login_info(token_data: TokenData = Depends(get_current_token_data)):
    async with aiohttp.ClientSession(cookie_jar=token_data.cookie_jar) as session:
        async with session.get("https://api.bilibili.com/x/space/acc/info",
                               params={"mid": token_data.user_id}) as response:
            return await response.json()
