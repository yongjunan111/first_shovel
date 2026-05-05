from pydantic import BaseModel


class AuthorizationURL(BaseModel):
    authorization_url: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # TODO: issue refresh_token once MVP auth flow stabilises.


class UserInfo(BaseModel):
    id: int
    email: str
    nickname: str
    provider: str
