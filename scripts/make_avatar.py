# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib", "numpy"]
# ///
"""生成「福裕伴读」小程序头像：青绿渐变底 + 翻开的书 + 对话气泡。"""
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, FancyBboxPatch, Circle

SIZE = 1024

# 主题色（与应用一致）
TEAL_LIGHT = np.array([0x22, 0x90, 0x7B]) / 255
TEAL_DEEP = np.array([0x14, 0x54, 0x47]) / 255
CREAM = "#f7f3e8"
CREAM_SHADE = "#e9e2cf"

fig = plt.figure(figsize=(SIZE / 100, SIZE / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# ---- 对角渐变背景 ----
n = 512
t = (np.add.outer(np.linspace(0, 1, n), np.linspace(0, 1, n)) / 2)[..., None]
grad = (TEAL_LIGHT * (1 - t) + TEAL_DEEP * t).astype(float)
ax.imshow(grad, extent=[0, 1, 0, 1], origin="lower", zorder=0)

# ---- 翻开的书（下半部居中）----
def page(right: bool) -> Path:
    s = 1 if right else -1
    verts = [
        (0.5, 0.30),                       # 书脊底部
        (0.5 + s * 0.17, 0.27),            # 底边外角（贝塞尔控制）
        (0.5 + s * 0.30, 0.31),
        (0.5 + s * 0.31, 0.33),
        (0.5 + s * 0.31, 0.55),            # 外侧上角
        (0.5 + s * 0.26, 0.60),            # 顶边弧度（控制点）
        (0.5 + s * 0.10, 0.55),
        (0.5, 0.52),                       # 书脊顶部
        (0.5, 0.30),
    ]
    codes = [
        Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.CLOSEPOLY,
    ]
    return Path(verts, codes)

ax.add_patch(PathPatch(page(right=False), facecolor=CREAM, edgecolor="none", zorder=2))
ax.add_patch(PathPatch(page(right=True), facecolor=CREAM_SHADE, edgecolor="none", zorder=2))

# 书页上的横线（文字意象）
for yy, w in [(0.46, 0.17), (0.41, 0.17), (0.36, 0.12)]:
    for s in (-1, 1):
        ax.plot(
            [0.5 + s * 0.05, 0.5 + s * (0.05 + w)],
            [yy + 0.015, yy],
            color=TEAL_DEEP, lw=5, alpha=0.25, solid_capstyle="round", zorder=3,
        )

# ---- 对话气泡（书上方，带小尾巴指向书）----
bubble = FancyBboxPatch(
    (0.36, 0.66), 0.30, 0.15,
    boxstyle="round,pad=0.012,rounding_size=0.05",
    facecolor=CREAM, edgecolor="none", zorder=4,
)
ax.add_patch(bubble)
tail = Path(
    [(0.44, 0.67), (0.47, 0.60), (0.52, 0.67), (0.44, 0.67)],
    [Path.MOVETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY],
)
ax.add_patch(PathPatch(tail, facecolor=CREAM, edgecolor="none", zorder=4))

# 气泡里的三个圆点（正在回答）
for i, xx in enumerate((0.455, 0.51, 0.565)):
    ax.add_patch(Circle((xx, 0.738), 0.021, facecolor=TEAL_DEEP, edgecolor="none", zorder=5))

fig.savefig("assets/mp-avatar.png", dpi=100)
print("saved assets/mp-avatar.png")
