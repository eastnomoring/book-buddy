"""公式渲染服务：用 matplotlib mathtext 把 LaTeX 渲染为 SVG。

用于小程序端等无 DOM 环境展示数学公式（方案文档 §5 方案 1）。
mathtext 不需要完整 LaTeX 环境，纯 Python 即可，适合服务端。
"""
import io
from typing import Literal

import matplotlib

matplotlib.use("Agg")  # 无头模式，必须在导入 pyplot 前设置
import matplotlib.pyplot as plt


Format = Literal["svg", "png"]


class FormulaRenderer:
    """LaTeX 公式 → SVG/PNG 图片"""

    def render(self, latex: str, format: Format = "svg") -> tuple[bytes, str]:
        """
        渲染 LaTeX 公式为图片。

        Args:
            latex: LaTeX 公式（不含 $ 定界符，如 r"E[X]=\\int x f(x)dx"）
            format: svg 或 png

        Returns:
            (图片字节, content_type)
        """
        if not latex or not latex.strip():
            raise ValueError("公式内容为空")

        content_type = "image/svg+xml" if format == "svg" else "image/png"

        try:
            fig = plt.figure(figsize=(0.01, 0.01))
            # mathtext 要求公式以 $ 包裹
            fig.text(0, 0, f"${latex}$", fontsize=20)
            buf = io.BytesIO()
            fig.savefig(
                buf,
                format=format,
                bbox_inches="tight",
                pad_inches=0.1,
                transparent=True,
                dpi=150,
            )
            plt.close(fig)
            data = buf.getvalue()
            if not data:
                raise RuntimeError("渲染产出为空")
            return data, content_type
        except ValueError as e:
            # mathtext 解析失败会抛 ValueError
            plt.close("all")
            raise ValueError(f"公式语法错误: {str(e)}") from e
        except Exception as e:
            plt.close("all")
            raise RuntimeError(f"渲染失败: {str(e)}") from e


# 全局实例
formula_renderer = FormulaRenderer()
