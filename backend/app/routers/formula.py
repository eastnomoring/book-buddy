"""公式渲染路由"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.formula import formula_renderer

router = APIRouter()

# LaTeX 长度上限：防超长输入拖垮 mathtext 渲染（CPU/内存密集）
MAX_LATEX_LENGTH = 800


@router.get("/render/formula")
async def render_formula(
    latex: str = Query(..., description="LaTeX 公式，不含 $ 定界符"),
    format: str = Query("svg", description="svg 或 png"),
):
    """
    渲染 LaTeX 公式为 SVG/PNG 图片。

    用于小程序端等无 DOM 环境展示数学公式。
    小程序端用法：``<image src="{{apiBase}}/render/formula?latex=...&format=svg" />``

    示例：
        GET /api/render/formula?latex=E[X]=\\int xf(x)dx&format=svg
    """
    if len(latex) > MAX_LATEX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"公式过长（{len(latex)} 字符，上限 {MAX_LATEX_LENGTH}）",
        )
    if format not in ("svg", "png"):
        raise HTTPException(status_code=400, detail="format 只支持 svg 或 png")

    try:
        data, content_type = formula_renderer.render(latex, format)
    except ValueError as e:
        # 公式语法错误
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return Response(content=data, media_type=content_type)
