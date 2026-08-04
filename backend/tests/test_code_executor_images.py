"""Z1: 代码执行图片输出测试。

真实执行 matplotlib 画图，验证图片被正确收集为 base64。
覆盖：有图/无图/图片超限截断 三条路径。

注意：matplotlib 首次运行会构建字体缓存（~10s），测试用 30s 超时避免误判。
"""
import pytest

from app.mcp.code_executor import run_python, MAX_IMAGES

# 测试专用超时（matplotlib 字体缓存构建慢）
TEST_TIMEOUT = 30


# matplotlib 画图代码模板（aggregation-safe：每段代码自己建 figure）
PLOT_CODE = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.figure()
plt.plot([1, 2, 3, 4], [1, 4, 9, 16])
plt.title('test')
plt.savefig('output.png')
plt.close()
"""

PLOT_CODE_JPG = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.figure()
plt.plot([1, 2], [3, 4])
plt.savefig('output.jpg')
plt.close()
"""


def test_collect_png_image():
    """执行画图代码，收集到 PNG 图片"""
    result = run_python(PLOT_CODE, timeout=TEST_TIMEOUT)
    assert result.exit_code == 0
    assert len(result.images) == 1
    img = result.images[0]
    assert img["mediaType"] == "image/png"
    # base64 解码后是合法 PNG（魔数头）
    import base64
    raw = base64.b64decode(img["base64"])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_collect_jpg_image():
    """JPG 图片 mediaType 正确"""
    result = run_python(PLOT_CODE_JPG, timeout=TEST_TIMEOUT)
    assert result.exit_code == 0
    assert len(result.images) >= 1
    media_types = [img["mediaType"] for img in result.images]
    assert "image/jpeg" in media_types


def test_no_image_when_no_plot():
    """不画图时 images 为空"""
    result = run_python("print('hello')")
    assert result.exit_code == 0
    assert result.images == []


def test_multiple_images_collected():
    """多张图片按修改时间收集"""
    code = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
for i in range(3):
    plt.figure()
    plt.plot([i, i+1])
    plt.savefig(f'fig_{i}.png')
    plt.close()
"""
    result = run_python(code, timeout=TEST_TIMEOUT)
    assert result.exit_code == 0
    assert len(result.images) == 3
    # 都是 PNG
    assert all(img["mediaType"] == "image/png" for img in result.images)


def test_image_count_capped():
    """超过 MAX_IMAGES 张时只收集前 MAX_IMAGES 张"""
    code_lines = [
        "import matplotlib; matplotlib.use('Agg')",
        "import matplotlib.pyplot as plt",
    ]
    for i in range(MAX_IMAGES + 3):
        code_lines.append(f"plt.figure(); plt.plot([{i}]); plt.savefig('f{i}.png'); plt.close()")
    code = "\n".join(code_lines)

    result = run_python(code, timeout=TEST_TIMEOUT)
    assert result.exit_code == 0
    assert len(result.images) == MAX_IMAGES


def test_tool_result_images_in_registry():
    """registry 调用 run_python 后返回 dict 带 images 字段（用简单图避免超时）"""
    from app.mcp.registry import _format_exec_result
    from app.mcp.code_executor import ExecutionResult

    # 直接构造带图的结果，验证 _format_exec_result 输出格式
    result = ExecutionResult(
        stdout="", stderr="", exit_code=0,
        images=[{"base64": "abc", "mediaType": "image/png"}],
    )
    formatted = _format_exec_result(result)
    assert formatted["images"] == [{"base64": "abc", "mediaType": "image/png"}]
    assert "生成了 1 张图片" in formatted["text"]
