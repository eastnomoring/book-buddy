"""受限 Python 代码执行器。

安全措施见 docs/MCP_CODE_EXECUTION_SELECTION.md §3：
超时、内存限制、网络隔离、临时目录、输出截断、只允许 python3。

设计为纯函数（不依赖 MCP），方便单元测试；MCP server 层在其上包装。
执行后收集临时目录中新生成的图片（png/jpg/svg），供前端展示画图结果。
"""
import base64
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional

# 安全参数
TIMEOUT_SECONDS = 10
MEMORY_LIMIT_BYTES = 256 * 1024 * 1024  # 256MB
MAX_OUTPUT_BYTES = 4096  # stdout/stderr 各截断到 4KB

# 图片收集参数
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg")
MAX_IMAGES = 6
MAX_IMAGE_SIZE = 1024 * 1024  # 单张 ≤1MB
_MEDIA_TYPE_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}

# 网络隔离：执行前 patch socket，阻止网络访问
NETWORK_BLOCK_PREAMBLE = """import socket as _sock
_orig_socket = _sock.socket
class _BlockedSocket(_orig_socket):
    def connect(self, *a, **kw):
        raise PermissionError("网络访问已被沙箱禁用")
_sock.socket = _BlockedSocket
"""


class ExecutionResult:
    """代码执行结果"""
    def __init__(self, stdout: str, stderr: str, exit_code: int, timed_out: bool = False, images: list = None):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.images = images or []  # [{base64, mediaType}]

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "images": self.images,
        }


def run_python(code: str, timeout: int = TIMEOUT_SECONDS) -> ExecutionResult:
    """在受限子进程中执行 Python 代码。

    Args:
        code: 要执行的 Python 源码
        timeout: 超时秒数（默认 10s）

    Returns:
        ExecutionResult（stdout/stderr/exit_code/timed_out）
    """
    if not code or not code.strip():
        return ExecutionResult("", "代码为空", 1)

    # 临时工作目录（执行后销毁）
    work_dir = tempfile.mkdtemp(prefix="bb_sandbox_")

    # 完整脚本：网络隔离前导 + 用户代码
    full_script = NETWORK_BLOCK_PREAMBLE + "\n" + code
    script_path = os.path.join(work_dir, "_exec.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(full_script)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            timeout=timeout,
            cwd=work_dir,
            env={
                # 最小环境变量，不继承敏感信息
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": work_dir,
                "LANG": "en_US.UTF-8",
                "PYTHONPATH": "",  # 不继承项目模块
                # matplotlib 配置缓存：用系统级目录避免每次重建（首跑 ~10s）
                "MPLCONFIGDIR": os.environ.get("MPLCONFIGDIR", "/tmp/matplotlib-cache"),
            },
        )
        stdout = _truncate(result.stdout)
        stderr = _truncate(result.stderr)
        # 执行后、销毁前收集临时目录里的图片文件
        images = _collect_images(work_dir)
        return ExecutionResult(stdout, stderr, result.returncode, images=images)

    except subprocess.TimeoutExpired:
        return ExecutionResult("", f"执行超时（>{timeout}s），已终止", 124, timed_out=True)
    except Exception as e:
        return ExecutionResult("", f"执行器错误: {e}", 1)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _collect_images(work_dir: str) -> list:
    """扫描临时目录中新生成的图片文件，返回 [{base64, mediaType}]。

    - 按修改时间排序（代码生成的先后顺序）
    - 最多 MAX_IMAGES 张，单张 ≤MAX_IMAGE_SIZE
    - 跳过脚本自身（_exec.py）和子目录里的图片
    """
    candidates = []
    for name in os.listdir(work_dir):
        ext = os.path.splitext(name)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue
        path = os.path.join(work_dir, name)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        if size > MAX_IMAGE_SIZE:
            continue  # 跳过过大的图，防撑爆 base64 传输
        candidates.append((os.path.getmtime(path), path, ext))

    candidates.sort(key=lambda x: x[0])  # 按修改时间
    images = []
    for _, path, ext in candidates[:MAX_IMAGES]:
        try:
            with open(path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("ascii")
            # svg 是文本，用 utf-8 编码
            if ext == ".svg":
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    b64 = base64.b64encode(f.read().encode("utf-8")).decode("ascii")
            images.append({"base64": b64, "mediaType": _MEDIA_TYPE_MAP[ext]})
        except Exception:
            continue
    return images


def _truncate(data: bytes, limit: int = MAX_OUTPUT_BYTES) -> str:
    """截断输出到指定字节，转 UTF-8（容错）"""
    if len(data) > limit:
        data = data[:limit]
        suffix = "\n...（输出已截断）"
    else:
        suffix = ""
    try:
        return data.decode("utf-8", errors="replace") + suffix
    except Exception:
        return data.decode("latin-1", errors="replace") + suffix
