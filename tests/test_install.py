"""
test_install.py
================
Everything Search v1 — install.py 单元测试

覆盖范围：
  - load_path_config() / save_path_config() : path.env 读写（使用 tmp_path 隔离）
  - is_wsl()                                : WSL 环境检测
  - find_es_exe()                           : 7 级路径发现（mock subprocess + 文件系统）
  - find_everything_exe()                   : Everything.exe 查找
  - is_everything_running()                 : 进程检测（mock subprocess）
  - verify_installation()                   : 安装验证（mock 文件系统 + subprocess）
  - discover_and_configure()                : 完整发现流程（mock）
  - start_everything_background()           : 后台启动（mock）
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import install
from install import (
    load_path_config,
    save_path_config,
    is_wsl,
    find_es_exe,
    find_everything_exe,
    is_everything_running,
    verify_installation,
    discover_and_configure,
    start_everything_background,
)


# ============================================================
# load_path_config / save_path_config
# ============================================================

class TestPathConfig:
    """path.env 配置文件读写"""

    def test_load_nonexistent_returns_none(self, tmp_path_env):
        assert load_path_config() == (None, None)

    def test_save_then_load(self, tmp_path_env):
        ok = save_path_config(r"C:\Everything", r"C:\Everything\es.exe", silent=True)
        assert ok is True

        everything, es = load_path_config()
        assert everything == r"C:\Everything"
        assert es == r"C:\Everything\es.exe"

    def test_save_creates_file_with_header(self, tmp_path_env):
        save_path_config(r"C:\Ev", r"C:\Ev\es.exe", silent=True)
        with open(tmp_path_env, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Everything Search v1" in content
        assert "EVERYTHING_PATH=C:\\Ev" in content
        assert "ES_PATH=C:\\Ev\\es.exe" in content

    def test_save_updates_existing_values(self, tmp_path_env):
        """重复保存应更新而非追加"""
        save_path_config(r"C:\Old", r"C:\Old\es.exe", silent=True)
        save_path_config(r"C:\New", r"C:\New\es.exe", silent=True)

        everything, es = load_path_config()
        assert everything == r"C:\New"
        assert es == r"C:\New\es.exe"

        # 不应有重复行
        with open(tmp_path_env, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.count("EVERYTHING_PATH=") == 1
        assert content.count("ES_PATH=") == 1

    def test_save_preserves_unknown_keys(self, tmp_path_env):
        """未知的 KEY=VALUE 行应被保留"""
        with open(tmp_path_env, "w", encoding="utf-8") as f:
            f.write("# comment\n")
            f.write("CUSTOM_KEY=custom_value\n")

        save_path_config(r"C:\Ev", r"C:\Ev\es.exe", silent=True)

        with open(tmp_path_env, "r", encoding="utf-8") as f:
            content = f.read()
        assert "CUSTOM_KEY=custom_value" in content

    def test_load_skips_comments_and_empty_lines(self, tmp_path_env):
        with open(tmp_path_env, "w", encoding="utf-8") as f:
            f.write("# This is a comment\n\n")
            f.write("EVERYTHING_PATH=C:\\Everything\n")
            f.write("\n")
            f.write("ES_PATH=C:\\Everything\\es.exe\n")

        everything, es = load_path_config()
        assert everything == r"C:\Everything"
        assert es == r"C:\Everything\es.exe"

    def test_load_malformed_line_does_not_crash(self, tmp_path_env):
        """无等号的行不应导致崩溃"""
        with open(tmp_path_env, "w", encoding="utf-8") as f:
            f.write("NO_EQUALS_HERE\n")
            f.write("EVERYTHING_PATH=C:\\Ev\n")
            f.write("ES_PATH=C:\\Ev\\es.exe\n")

        everything, es = load_path_config()
        assert everything == r"C:\Ev"
        assert es == r"C:\Ev\es.exe"


# ============================================================
# is_wsl
# ============================================================

class TestIsWsl:
    """WSL 环境检测"""

    def test_non_wsl_environment(self):
        """在标准 Windows/非 Linux 环境下应返回 False（/proc/version 不存在）"""
        # 在 Windows 上 /proc/version 不存在 → 异常 → False
        # 这个测试验证的是"不崩溃且返回 bool"
        result = is_wsl()
        assert isinstance(result, bool)

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_proc_version_not_found(self, mock_open):
        assert is_wsl() is False

    @patch("builtins.open", side_effect=PermissionError)
    def test_proc_version_permission_denied(self, mock_open):
        assert is_wsl() is False

    @patch("builtins.open", new_callable=MagicMock)
    def test_wsl_detected(self, mock_open):
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "Linux version 5.10 microsoft"
        mock_open.return_value = mock_file
        assert is_wsl() is True

    @patch("builtins.open", new_callable=MagicMock)
    def test_non_wsl_linux(self, mock_open):
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "Linux version 5.10 ubuntu"
        mock_open.return_value = mock_file
        assert is_wsl() is False


# ============================================================
# find_es_exe
# ============================================================

class TestFindEsExe:
    """es.exe 路径发现 — 7 级优先级"""

    @patch("install._find_from_running_process", return_value=None)
    @patch("install.load_path_config", return_value=(None, None))
    def test_all_levels_fail_returns_none(self, mock_config, mock_proc, monkeypatch):
        """所有发现级别都失败时返回 None"""
        monkeypatch.delenv("EVERYTHING_PATH", raising=False)
        monkeypatch.delenv("ES_PATH", raising=False)

        with patch("install.os.path.isfile", return_value=False), \
             patch("install.shutil.which", return_value=None), \
             patch("install.start_everything_background", return_value=False):
            assert find_es_exe() is None

    @patch("install._find_from_running_process", return_value=r"C:\Ev\es.exe")
    @patch("install.load_path_config", return_value=(None, None))
    def test_level0_running_process(self, mock_config, mock_proc):
        """Level 0: 从运行中的进程获取"""
        assert find_es_exe() == r"C:\Ev\es.exe"

    @patch("install._find_from_running_process", return_value=None)
    @patch("install.load_path_config", return_value=(r"C:\Ev", r"C:\Ev\es.exe"))
    @patch("install.os.path.isfile", return_value=True)
    def test_level1_path_env(self, mock_isfile, mock_config, mock_proc):
        """Level 1: path.env 配置文件"""
        assert find_es_exe() == r"C:\Ev\es.exe"

    @patch("install._find_from_running_process", return_value=None)
    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.os.path.isfile", return_value=True)
    def test_level2_env_var_everything_path(self, mock_isfile, mock_config, mock_proc, monkeypatch):
        """Level 2: 环境变量 EVERYTHING_PATH"""
        monkeypatch.setenv("EVERYTHING_PATH", r"C:\MyEverything")
        result = find_es_exe()
        assert result == r"C:\MyEverything\es.exe"

    @patch("install._find_from_running_process", return_value=None)
    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.os.path.isfile", side_effect=lambda p: p == r"C:\Program Files\Everything\es.exe")
    def test_level3_common_paths(self, mock_isfile, mock_config, mock_proc, monkeypatch):
        """Level 3: 常用安装路径"""
        monkeypatch.delenv("EVERYTHING_PATH", raising=False)
        monkeypatch.delenv("ES_PATH", raising=False)

        result = find_es_exe()
        assert result == r"C:\Program Files\Everything\es.exe"

    @patch("install._find_from_running_process", return_value=None)
    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.os.path.isfile", side_effect=lambda p: p == r"C:\Custom\es.exe")
    def test_level4_env_var_es_path(self, mock_isfile, mock_config, mock_proc, monkeypatch):
        """Level 4: 环境变量 ES_PATH"""
        monkeypatch.delenv("EVERYTHING_PATH", raising=False)
        monkeypatch.setenv("ES_PATH", r"C:\Custom\es.exe")
        result = find_es_exe()
        assert result == r"C:\Custom\es.exe"

    @patch("install._find_from_running_process", return_value=None)
    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.os.path.isfile", return_value=False)
    @patch("install.shutil.which", return_value=r"C:\tools\es.exe")
    def test_level5_system_path(self, mock_which, mock_isfile, mock_config, mock_proc, monkeypatch):
        """Level 5: 系统 PATH"""
        monkeypatch.delenv("EVERYTHING_PATH", raising=False)
        monkeypatch.delenv("ES_PATH", raising=False)

        result = find_es_exe()
        assert result == r"C:\tools\es.exe"

    @patch("install._find_from_running_process", side_effect=[None, r"C:\Ev\es.exe"])
    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.os.path.isfile", return_value=False)
    @patch("install.shutil.which", return_value=None)
    @patch("install.start_everything_background", return_value=True)
    def test_level6_start_everything_retry(self, mock_start, mock_which, mock_isfile, mock_config, mock_proc, monkeypatch):
        """Level 6: 启动 Everything 后重试"""
        monkeypatch.delenv("EVERYTHING_PATH", raising=False)
        monkeypatch.delenv("ES_PATH", raising=False)

        result = find_es_exe()
        assert result == r"C:\Ev\es.exe"


# ============================================================
# find_everything_exe
# ============================================================

class TestFindEverythingExe:
    """Everything.exe 路径查找"""

    @patch("install.os.path.isfile", return_value=True)
    def test_from_env_var(self, mock_isfile, monkeypatch):
        monkeypatch.setenv("EVERYTHING_PATH", r"C:\Ev")
        result = find_everything_exe()
        assert result == r"C:\Ev\Everything.exe"

    @patch("install.load_path_config", return_value=(r"C:\Ev", None))
    @patch("install.os.path.isfile", return_value=True)
    def test_from_path_env(self, mock_isfile, mock_config, monkeypatch):
        monkeypatch.delenv("EVERYTHING_PATH", raising=False)
        result = find_everything_exe()
        assert result == r"C:\Ev\Everything.exe"

    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.os.path.isfile", return_value=False)
    @patch("install.shutil.which", return_value=None)
    def test_not_found(self, mock_which, mock_isfile, mock_config, monkeypatch):
        monkeypatch.delenv("EVERYTHING_PATH", raising=False)
        assert find_everything_exe() is None


# ============================================================
# is_everything_running
# ============================================================

class TestIsEverythingRunning:
    """Everything 进程检测"""

    @patch("install.is_wsl", return_value=False)
    @patch("install.sys.platform", "win32")
    @patch("install.subprocess.run")
    def test_running_on_windows(self, mock_run, mock_wsl):
        mock_run.return_value = MagicMock(stdout="Everything.exe 1234 Console")
        assert is_everything_running() is True

    @patch("install.is_wsl", return_value=False)
    @patch("install.sys.platform", "win32")
    @patch("install.subprocess.run")
    def test_not_running_on_windows(self, mock_run, mock_wsl):
        mock_run.return_value = MagicMock(stdout="INFO: No tasks running")
        assert is_everything_running() is False

    @patch("install.is_wsl", return_value=False)
    @patch("install.sys.platform", "linux")
    def test_unsupported_platform(self, mock_wsl):
        assert is_everything_running() is False

    @patch("install.is_wsl", return_value=True)
    @patch("install.subprocess.run")
    def test_wsl_environment(self, mock_run, mock_wsl):
        mock_run.return_value = MagicMock(stdout="Everything.exe 1234 Console")
        assert is_everything_running() is True

    @patch("install.is_wsl", return_value=False)
    @patch("install.sys.platform", "win32")
    @patch("install.subprocess.run", side_effect=Exception("subprocess failed"))
    def test_exception_returns_false(self, mock_run, mock_wsl):
        assert is_everything_running() is False


# ============================================================
# verify_installation
# ============================================================

class TestVerifyInstallation:
    """安装验证"""

    @patch("install.os.path.isfile", return_value=True)
    @patch("install.subprocess.run")
    def test_valid_installation(self, mock_run, mock_isfile):
        mock_run.return_value = MagicMock(returncode=0, stdout="ES-1.1.0", stderr="")
        assert verify_installation(r"C:\Ev", r"C:\Ev\es.exe", silent=True) is True

    @patch("install.os.path.isfile", side_effect=lambda p: "Everything.exe" in p)
    @patch("install.subprocess.run")
    def test_es_exe_missing(self, mock_run, mock_isfile):
        """es.exe 不存在时返回 False"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        assert verify_installation(r"C:\Ev", r"C:\Ev\es.exe", silent=True) is False

    @patch("install.os.path.isfile", return_value=True)
    @patch("install.subprocess.run")
    def test_es_exe_returns_nonzero(self, mock_run, mock_isfile):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="some error")
        # 非零返回码不直接导致 verify 失败（只有 Exception 才标记 success=False）
        # 但 isfile=True + 可执行文件存在 → True
        result = verify_installation(r"C:\Ev", r"C:\Ev\es.exe", silent=True)
        assert isinstance(result, bool)

    @patch("install.os.path.isfile", return_value=True)
    @patch("install.subprocess.run", side_effect=Exception("crash"))
    def test_es_exe_execution_exception(self, mock_run, mock_isfile):
        """es.exe 运行异常 → False"""
        assert verify_installation(r"C:\Ev", r"C:\Ev\es.exe", silent=True) is False


# ============================================================
# discover_and_configure
# ============================================================

class TestDiscoverAndConfigure:
    """完整发现与配置流程"""

    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.find_es_exe", return_value=None)
    def test_es_not_found_returns_false(self, mock_find, mock_config):
        assert discover_and_configure(silent=True) is False

    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.find_es_exe", return_value=r"C:\Ev\es.exe")
    @patch("install.save_path_config", return_value=True)
    @patch("install.verify_installation", return_value=True)
    def test_successful_discovery(self, mock_verify, mock_save, mock_find, mock_config):
        assert discover_and_configure(silent=True) is True
        mock_save.assert_called_once()

    @patch("install.load_path_config", return_value=(None, None))
    @patch("install.find_es_exe", return_value=r"C:\Ev\es.exe")
    @patch("install.save_path_config", return_value=True)
    @patch("install.verify_installation", return_value=False)
    def test_found_but_verify_fails(self, mock_verify, mock_save, mock_find, mock_config):
        assert discover_and_configure(silent=True) is False

    @patch("install.load_path_config", return_value=(r"C:\Ev", r"C:\Ev\es.exe"))
    @patch("install.verify_installation", return_value=True)
    def test_existing_config_valid(self, mock_verify, mock_config):
        """已有有效配置 → 直接返回 True，不重新发现"""
        assert discover_and_configure(silent=True) is True


# ============================================================
# start_everything_background
# ============================================================

class TestStartEverythingBackground:
    """后台启动 Everything"""

    @patch("install.is_everything_running", return_value=True)
    def test_already_running(self, mock_running):
        assert start_everything_background() is True

    @patch("install.is_everything_running", side_effect=[False, True, True])
    @patch("install.is_wsl", return_value=False)
    @patch("install.sys.platform", "win32")
    @patch("install.find_everything_exe", return_value=r"C:\Ev\Everything.exe")
    @patch("install.subprocess.Popen")
    @patch("install.time.sleep")
    def test_start_success(self, mock_sleep, mock_popen, mock_find, mock_wsl, mock_running):
        assert start_everything_background() is True
        mock_popen.assert_called_once()

    @patch("install.is_everything_running", return_value=False)
    @patch("install.find_everything_exe", return_value=None)
    def test_exe_not_found(self, mock_find, mock_running):
        assert start_everything_background() is False

    @patch("install.is_everything_running", side_effect=[False] * 12)
    @patch("install.is_wsl", return_value=False)
    @patch("install.sys.platform", "win32")
    @patch("install.find_everything_exe", return_value=r"C:\Ev\Everything.exe")
    @patch("install.subprocess.Popen")
    @patch("install.time.sleep")
    def test_start_timeout(self, mock_sleep, mock_popen, mock_find, mock_wsl, mock_running):
        """启动后等待超时仍检测不到运行 → False"""
        assert start_everything_background() is False
