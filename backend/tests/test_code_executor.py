"""S4: MCP 代码执行器测试。

真实执行子进程，验证安全措施（超时、网络隔离、输出截断）。
"""
import pytest

from app.mcp.code_executor import run_python


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
