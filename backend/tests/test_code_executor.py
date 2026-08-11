"""S4: MCP 代码执行器测试。

真实执行子进程，验证安全措施（超时、内存限制、网络隔离、输出截断）。
"""
import os
import subprocess
import sys

import pytest

from app.mcp import code_executor
from app.mcp.code_executor import run_python


def _rlimit_as_enforceable() -> bool:
    """探测当前平台能否设置有限的 RLIMIT_AS。

    macOS 内核拒绝任何有限值（只允许 RLIM_INFINITY），Linux 正常。
    在子进程里探测，避免影响 pytest 进程自身。
    """
    if os.name != "posix":
        return False
    probe = (
        "import resource;"
        "resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))"
    )
    return subprocess.run(
        [sys.executable, "-c", probe], capture_output=True
    ).returncode == 0


def test_run_python_basic_output():
    """基本执行：print 输出正确捕获"""
    result = run_python("print('hello world')")
    assert result.exit_code == 0
    assert "hello world" in result.stdout


def test_run_python_math():
    """数值计算正确"""
    result = run_python("print(2 ** 10)")
    assert result.exit_code == 0
    assert "1024" in result.stdout


def test_run_python_captures_stderr():
    """stderr 被捕获"""
    result = run_python("import sys; sys.stderr.write('warn\\n')")
    assert result.exit_code == 0
    assert "warn" in result.stderr


def test_run_python_timeout():
    """超时被终止"""
    result = run_python("import time; time.sleep(30)", timeout=2)
    assert result.timed_out is True
    assert result.exit_code == 124
    assert "超时" in result.stderr


def test_run_python_network_blocked():
    """网络访问被沙箱阻止"""
    result = run_python("""
import socket
try:
    socket.create_connection(("8.8.8.8", 53), timeout=3)
    print("SHOULD_NOT_REACH_HERE")
except PermissionError as e:
    print("BLOCKED:", str(e)[:20])
""")
    assert result.exit_code == 0
    assert "BLOCKED" in result.stdout
    assert "SHOULD_NOT_REACH_HERE" not in result.stdout


def test_run_python_empty_code():
    """空代码返回错误"""
    result = run_python("")
    assert result.exit_code == 1
    assert "为空" in result.stderr


def test_run_python_exception_captured():
    """运行时异常被捕获到 stderr"""
    result = run_python("raise ValueError('test error')")
    assert result.exit_code != 0
    assert "test error" in result.stderr


def test_run_python_no_access_to_project_modules():
    """沙箱内不能 import 项目模块"""
    result = run_python("import app; print('LEAKED')")
    assert "LEAKED" not in result.stdout
    assert result.exit_code != 0


def test_run_python_memory_limit_enforced(monkeypatch):
    """超过内存上限的分配应失败（平台支持有限 RLIMIT_AS 时）。

    上限调到 128MB：高于解释器基线占用（~30MB，能正常启动），
    又低于测试分配的 300MB（必然触发 MemoryError），保持测试快速确定。
    """
    if not _rlimit_as_enforceable():
        pytest.skip("当前平台内核不支持有限 RLIMIT_AS（如 macOS）")

    monkeypatch.setattr(code_executor, "MEMORY_LIMIT_BYTES", 128 * 1024 * 1024)

    # 对照组：128MB 上限下解释器正常启动、小额分配正常
    ok = run_python("x = bytearray(8 * 1024 * 1024); print('fine')")
    assert ok.exit_code == 0
    assert "fine" in ok.stdout

    # 超限分配：MemoryError，而非静默成功
    result = run_python("x = bytearray(300 * 1024 * 1024); print('ALLOCATED')")
    assert result.exit_code != 0
    assert "ALLOCATED" not in result.stdout
    assert "MemoryError" in result.stderr


def test_run_python_memory_limit_degrades_gracefully(monkeypatch):
    """平台不支持 RLIMIT_AS 时（macOS）：限制被跳过，执行不因此崩溃。"""
    if _rlimit_as_enforceable():
        pytest.skip("当前平台支持 RLIMIT_AS，无需验证降级路径")

    # 调到 1MB：若限制真的生效连解释器都起不来，用于证明它确实被安全跳过
    monkeypatch.setattr(code_executor, "MEMORY_LIMIT_BYTES", 1024 * 1024)
    result = run_python("print('still works')")
    assert result.exit_code == 0
    assert "still works" in result.stdout
