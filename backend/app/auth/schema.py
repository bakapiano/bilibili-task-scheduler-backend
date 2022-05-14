from pydantic.main import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str
    cookie_jar: object
    # bili_jct: str
