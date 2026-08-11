"""Token 鉴权中间件（可选，默认关闭）。

部署到公网给小程序用时，通过环境变量 AUTH_TOKEN 开启：
  - 未设置 AUTH_TOKEN：中间件不生效（局域网自用模式）
  - 设置了 AUTH_TOKEN：所有 /api/* 请求需带 Authorization: Bearer <token>

小程序端在 wx.request header 里带 Authorization。
"""
import os

from fastapi import Request
from fastapi.responses import JSONResponse


async def auth_middleware(request: Request, call_next):
    """简易 Bearer token 校验中间件"""
    auth_token = os.environ.get("AUTH_TOKEN")

    # 未配置 token → 关闭鉴权，放行
    if not auth_token:
        return await call_next(request)

    # 只保护业务接口，放过健康检查与文档
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)

    # 校验 Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token == auth_token:
            return await call_next(request)

    return JSONResponse(
        status_code=401,
        content={"detail": "未授权：缺少或无效的 token"},
    )
