"""
Pytest 共享 fixtures 和路径配置
确保 tests/ 目录能正确导入 scripts/ 下的模块
"""

import os
import sys
import tempfile
import pytest

# 将 scripts/ 目录加入 sys.path，使测试可直接 import install / search_core
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture
def tmp_path_env(tmp_path, monkeypatch):
    """
    将 install.PATH_ENV_FILE 指向临时目录，避免污染真实的 path.env。
    返回临时 path.env 文件路径。
    """
    import install
    tmp_env = tmp_path / "path.env"
    monkeypatch.setattr(install, "PATH_ENV_FILE", str(tmp_env))
    # search_core 从 install 导入，但 PATH_ENV_FILE 是 install 模块级常量，
    # install 内部函数引用的是 install.PATH_ENV_FILE，monkeypatch 已覆盖。
    return str(tmp_env)
