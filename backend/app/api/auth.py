"""Auth endpoints: WeChat login stub."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class WxLoginRequest(BaseModel):
    code: str


@router.post("/wx-login")
async def wx_login(req: WxLoginRequest) -> dict[str, str]:
    """WeChat login stub — returns mock token in W1."""
    return {
        "token": "mock_token_w1",
        "openid": "mock_openid_123",
        "message": "登录成功（W1 mock）",
    }
