import pickle
from http.cookies import SimpleCookie

import aiohttp
from fastapi import Cookie, HTTPException, Header
from jose import jwt
from starlette import status

from backend.app.auth.const import SECRET_KEY, ALGORITHM
from backend.app.auth.schema import TokenData
from backend.lib.crawler import test_cookie_jar


async def get_current_token_data(authorization: str = Header(...)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(authorization, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        cookies: SimpleCookie = pickle.loads(str.encode(payload.get("cookies")))
        cookie_jar = aiohttp.CookieJar()
        cookie_jar._cookies = cookies
        bili_jct: str = cookies.get("bilibili.com").get("bili_jct").value
        if user_id is None or not await test_cookie_jar(cookie_jar):
            raise credentials_exception
        token_data = TokenData(user_id=user_id, cookie_jar=cookie_jar, bili_jct=bili_jct)
    except Exception as e:
        print(e)
        raise credentials_exception
    return token_data