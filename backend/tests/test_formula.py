"""公式渲染服务测试"""
import pytest

from app.services.formula import formula_renderer


def test_render_svg_basic():
    """渲染简单公式为 SVG"""
    data, content_type = formula_renderer.render(r"E[X]=\int x f(x) dx", "svg")
    assert isinstance(data, bytes)
    assert len(data) > 0
    assert content_type == "image/svg+xml"
    svg = data.decode("utf-8")
    assert "</svg>" in svg


def test_render_png_basic():
    """渲染简单公式为 PNG"""
    data, content_type = formula_renderer.render(r"\frac{a}{b}", "png")
    assert isinstance(data, bytes)
    assert len(data) > 0
    # PNG 魔数头
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert content_type == "image/png"


def test_render_fraction():
    """分式公式"""
    data, _ = formula_renderer.render(r"\frac{1}{2}", "svg")
    assert b"</svg>" in data


def test_render_sum_with_limits():
    """带上下限的求和"""
    data, _ = formula_renderer.render(r"\sum_{i=1}^{n} x_i", "svg")
    assert b"</svg>" in data


def test_render_empty_raises():
    """空公式应报错"""
    with pytest.raises(ValueError, match="为空"):
        formula_renderer.render("", "svg")
    with pytest.raises(ValueError, match="为空"):
        formula_renderer.render("   ", "svg")


def test_render_invalid_syntax_raises():
    """非法 LaTeX 语法应报 ValueError（422 给前端）"""
    with pytest.raises(ValueError):
        formula_renderer.render(r"\unknowncommand{x}", "svg")


def test_render_chinese_text_in_formula():
    """公式里允许中文（用于注释性公式）"""
    data, _ = formula_renderer.render(r"P(A) = 概率", "svg")
    assert b"</svg>" in data


def test_render_route_rejects_overlong_latex():
    """GET /api/render/formula 对超长 latex 返回 400（防拖垮 mathtext）"""
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    resp = client.get(
        "/api/render/formula",
        params={"latex": "x" * 801, "format": "svg"},
    )
    assert resp.status_code == 400
    assert "过长" in resp.json()["detail"]


def test_render_route_accepts_latex_at_limit():
    """恰好达到长度上限（800）的 latex 不被长度门拦截（由后续 format 校验证明已通过）"""
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    resp = client.get(
        "/api/render/formula",
        params={"latex": "x" * 800, "format": "gif"},  # 非法 format
    )
    # 命中的是 format 校验而非长度校验 → 说明长度门已放行
    assert resp.status_code == 400
    assert "format" in resp.json()["detail"]
