#!/usr/bin/env python3



import os
import sys
import ctypes
import subprocess
import shutil
import time
import re
from pathlib import Path
from typing import Optional, Tuple







EVERYTHING_COMMON_PATHS = [
    r"C:\Program Files\Everything",
    r"C:\Program Files (x86)\Everything",
    r"D:\Program Files\Everything",
    r"D:\Program Files (x86)\Everything",
]



EVERYTHING_DOWNLOAD_URL = "https://www.voidtools.com/zh-cn/downloads/"
ES_CLI_URL = "https://www.voidtools.com/zh-cn/downloads/#cli"
EVERYTHING_SUPPORT_URL = "https://www.voidtools.com/zh-cn/support/everything/"


PATH_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "path.env")






def print_header(title: str) -> None:
    """打印带装饰的标题"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def print_success(message: str) -> None:
    """打印成功信息"""
    print(f"  ✅ {message}")


def print_warning(message: str) -> None:
    """打印警告信息"""
    print(f"  ⚠️  {message}")


def print_error(message: str) -> None:
    """打印错误信息"""
    print(f"  ❌ {message}")


def print_not_found(message: str) -> None:
    """打印"未找到"类错误（🔴 前缀，与 search_core.py 的错误风格一致）"""
    print(f"  🔴 {message}")


def print_info(message: str) -> None:
    """打印信息"""
    print(f"  ℹ️  {message}")







def _find_from_running_process() -> Optional[str]:
    
    try:

        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process -Name 'Everything' -ErrorAction SilentlyContinue).Path"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10
        )
        
        for line in result.stdout.strip().split(chr(10)):
            line = line.strip()
            if line and os.path.isfile(line):
                everything_dir = os.path.dirname(line)
                return _exists_exe(everything_dir, "es.exe")
    except Exception:
        pass
    
    return None


def _find_in_common_paths(target_exe: str) -> Optional[str]:
    """在 EVERYTHING_COMMON_PATHS 列出的常见安装目录下查找指定 exe，返回完整路径"""
    for base_path in EVERYTHING_COMMON_PATHS:
        cand = os.path.join(base_path, target_exe)
        if os.path.isfile(cand):
            return cand
    return None


def _exists_exe(directory: str, name: str) -> Optional[str]:
    """若 directory/name 存在则返回其完整路径，否则 None（directory 为空直接返回 None）"""
    if not directory:
        return None
    cand = os.path.join(directory, name)
    return cand if os.path.isfile(cand) else None


def find_es_exe() -> Optional[str]:
    
    cfg = read_env_dict()


    manual_es = cfg.get("ES_PATH")
    if manual_es and os.path.isfile(manual_es):
        return manual_es


    found = _find_from_running_process()
    if found:
        return found


    ep = os.environ.get("EVERYTHING_PATH")
    found = _exists_exe(ep, "es.exe")
    if found:
        return found


    found = _find_in_common_paths("es.exe")
    if found:
        return found


    es_env = os.environ.get("ES_PATH")
    if es_env and os.path.isfile(es_env):
        return es_env


    in_path = shutil.which("es") or shutil.which("es.exe")
    if in_path:
        return in_path

    return None


def find_everything_exe() -> Optional[str]:
    
    cfg = read_env_dict()


    manual_exe = cfg.get("EVERYTHING_PATH")
    if manual_exe and os.path.isfile(manual_exe):
        return manual_exe


    ep = os.environ.get("EVERYTHING_PATH")
    found = _exists_exe(ep, "Everything.exe")
    if found:
        return found


    found = _find_in_common_paths("Everything.exe")
    if found:
        return found


    in_path = shutil.which("Everything")
    if in_path:
        return in_path

    return None


def is_wsl() -> bool:
    
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except Exception:
        return False


def is_everything_running() -> bool:
    
    try:
        if is_wsl():

            result = subprocess.run(
                ["cmd.exe", "/c", "tasklist", "/FI", "IMAGENAME eq Everything.exe"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=10
            )
        elif sys.platform == 'win32':

            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Everything.exe"],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
        else:
            return False
        return "Everything.exe" in result.stdout
    except Exception:
        return False


def _shell_execute_open(target: str, args: Optional[str] = None) -> bool:
    
    try:

        ctypes.windll.shell32.ShellExecuteW.restype = ctypes.c_int
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "open",
            target,
            args or "",
            None,
            1
        )

        return isinstance(result, int) and result > 32
    except Exception:
        return False


def _is_es_reachable() -> bool:
    
    es_path = find_es_exe()
    if not es_path:
        return False
    try:
        result = subprocess.run(
            [es_path, "-max-results", "1", "zzz_es_ipc_probe"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception:
        return False
    out = (result.stdout + result.stderr).lower()
    if "ipc window not found" in out or "error 8" in out:
        return False
    return True


def _wait_until(predicate, tries: int = 10, interval: float = 0.5) -> bool:
    
    for _ in range(tries):
        time.sleep(interval)
        if predicate():
            return True
    return predicate()


def start_everything_background() -> bool:
    
    try:
        if is_wsl():

            if is_everything_running():
                return True
            everything_exe = find_everything_exe()
            if not everything_exe:
                return False
            subprocess.Popen(
                [everything_exe, "-startup"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return _wait_until(is_everything_running)

        if sys.platform != 'win32':
            return False




        if _is_es_reachable():
            return True

        everything_exe = find_everything_exe()
        if not everything_exe:
            return False



        launched = _shell_execute_open(everything_exe, "-startup")
        if not launched:

            print_warning("ShellExecute 启动失败，回退到 subprocess 方式")
            subprocess.Popen(
                [everything_exe, "-startup"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )


        return _wait_until(_is_es_reachable)
    except Exception:
        return False






_ENV_KEY_ORDER = [
    "EVERYTHING_PATH",
    "ES_PATH",
]


def read_env_dict() -> dict:
    
    config: dict = {}
    if not os.path.isfile(PATH_ENV_FILE):
        return config
    try:
        with open(PATH_ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    except Exception:
        return {}
    return config


def _write_env_dict(config: dict, *, manual: bool = False, subject: str = "配置") -> bool:
    
    try:
        import datetime
        os.makedirs(os.path.dirname(PATH_ENV_FILE), exist_ok=True)
        keys = [k for k in _ENV_KEY_ORDER if k in config]
        keys += [k for k in config if k not in _ENV_KEY_ORDER]
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        mode = "手动" if manual else "自动"
        with open(PATH_ENV_FILE, 'w', encoding='utf-8') as f:
            f.write("# Everything-Search-Skill 路径配置文件\n")
            f.write("# 此文件由脚本自动生成和更新\n")
            f.write(f"#更新时间：{ts}，{mode}更新了{subject}配置\n")
            for key in keys:
                f.write(f"{key}={config[key]}\n")
        return True
    except Exception:
        return False


def update_path_config(
    everything_path: Optional[str] = None,
    es_path: Optional[str] = None,
    manual: bool = False,
    silent: bool = False,
) -> bool:
    
    try:
        config = read_env_dict()

        config.pop("EVERYTHING_PATH_SOURCE", None)
        config.pop("ES_PATH_SOURCE", None)
        changed = False
        updated = []

        if everything_path is not None:
            config["EVERYTHING_PATH"] = everything_path
            changed = True
            updated.append("Everything.exe")

        if es_path is not None:
            config["ES_PATH"] = es_path
            changed = True
            updated.append("es.exe")

        if not changed:
            return True

        subject = "Everything.exe和es.exe" if len(updated) == 2 else updated[0]
        if not _write_env_dict(config, manual=manual, subject=subject):
            if not silent:
                print_error("保存配置失败: 无法写入 path.env")
            return False

        if not silent:
            print_success(f"路径配置已保存到: {os.path.normpath(PATH_ENV_FILE)}")
        return True
    except Exception as e:
        if not silent:
            print_error(f"保存配置失败: {e}")
        return False


def save_path_config(everything_path: str, es_path: str, silent: bool = False) -> bool:
    
    return update_path_config(everything_path=everything_path, es_path=es_path, manual=False, silent=silent)


def load_path_config() -> Tuple[Optional[str], Optional[str]]:
    
    config = read_env_dict()
    return config.get("EVERYTHING_PATH"), config.get("ES_PATH")






def _probe_es_version(es_path: str) -> Tuple[str, Optional[str]]:
    
    if not os.path.isfile(es_path):
        return ("error", None)
    try:
        result = subprocess.run(
            [es_path, "-version"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
        )
    except Exception:
        return ("error", None)
    if result.returncode != 0:
        return ("nonzero", None)
    first_line = (result.stdout or "").strip().splitlines()
    return ("ok", first_line[0].strip() if first_line else "")


def verify_installation(everything_path: str, es_path: str, silent: bool = False) -> bool:
    
    if not silent:
        print()
        print_header("验证安装")

    success = True


    everything_exe = everything_path
    if os.path.isfile(everything_exe):
        if not silent:
            print_success(f"Everything.exe 存在: {everything_exe}")
    else:
        if not silent:
            print_error(f"Everything.exe 不存在: {everything_exe}")
        success = False


    if os.path.isfile(es_path):
        if not silent:
            print_success(f"es.exe 存在: {es_path}")
        status, _ = _probe_es_version(es_path)
        if status == "ok":
            if not silent:
                print_success("es.exe 可正常运行")
        elif status == "nonzero":
            if not silent:
                print_warning("es.exe 返回非零状态码（文件校验通过，但运行测试未完全通过）")
        else:
            if not silent:
                print_error("es.exe 运行测试失败")
            success = False
    else:
        if not silent:
            print_error(f"es.exe 不存在: {es_path}")
        success = False

    return success






def _lookup_in_dir(dir_path: str, target_name: str) -> Optional[str]:
    
    direct = os.path.join(dir_path, target_name)
    if os.path.isfile(direct):
        return direct
    try:
        target_lower = target_name.lower()
        for entry in os.listdir(dir_path):
            if entry.lower() == target_lower:
                candidate = os.path.join(dir_path, entry)
                if os.path.isfile(candidate):
                    return candidate
    except Exception:
        pass
    return None


def _normalize_input_path(raw: str) -> str:
    """清洗用户输入的路径：去首尾空白/引号、展开环境变量与 ~、转绝对路径"""
    cleaned = raw.strip().strip('"').strip("'").strip()
    cleaned = os.path.expandvars(os.path.expanduser(cleaned))

    if len(cleaned) > 3:
        cleaned = re.sub(r'[\\/]+$', '', cleaned)
    return os.path.abspath(cleaned) if cleaned else cleaned


def _print_current_config() -> None:
    """打印 path.env 中当前生效的配置"""
    config = read_env_dict()
    everything_path = config.get("EVERYTHING_PATH")
    es_path = config.get("ES_PATH")
    print()
    print("  📄 当前 path.env 配置:")
    if everything_path:
        print(f"     EVERYTHING_PATH = {everything_path}")
    else:
        print("     EVERYTHING_PATH = (未设置)")
    if es_path:
        print(f"     ES_PATH         = {es_path}")
    else:
        print("     ES_PATH         = (未设置)")


def _verify_es_runnable(es_path: str) -> None:
    """轻量验证 es.exe 是否可运行（非致命，仅提示），复用 _probe_es_version"""
    status, version = _probe_es_version(es_path)
    if status == "ok" and version:
        print_success(f"es.exe 可正常运行（版本 {version}）")
    elif status == "ok":
        print_success("es.exe 可正常运行")
    else:
        print_warning("es.exe 运行测试未通过（非零退出码或无法运行，不影响路径保存）")


def _save_manual_path(**kwargs) -> bool:
    """以 manual 模式写入 path.env；失败打印错误并返回 False（成功返回 True）"""
    if update_path_config(manual=True, silent=True, **kwargs):
        return True
    print_error("保存配置失败: 无法写入 path.env")
    return False


def install_from_path(target: Optional[str]) -> int:
    
    print_header("Everything Search - 手动配置路径 (--install)")

    if not target or not target.strip():
        script = os.path.basename(sys.argv[0]) or "install.py"
        print_not_found("未提供路径，请输入正确的路径")
        print()
        print("  用法示例:")
        print(rf'    python {script} "D:\Everything1.4" --install                 # 目录：同时更新两者')
        print(rf'    python {script} "D:\Everything1.4\es.exe" --install          # 只更新 es.exe')
        print(rf'    python {script} "D:\Everything1.4\Everything.exe" --install  # 只更新 Everything')
        return 1

    path = _normalize_input_path(target)
    basename = os.path.basename(path).lower()


    if basename in ("es.exe", "everything.exe"):
        display_name = "es.exe" if basename == "es.exe" else "Everything.exe"
        print_info(f"目标: {path}")
        print_info(f"模式: 单文件（仅更新 {display_name} 路径）")
        print()

        if not os.path.isfile(path):
            print_not_found(f"未找到 {display_name}: {path}")
            print_not_found("请输入正确的路径")
            return 1

        if basename == "es.exe":
            if not _save_manual_path(es_path=path):
                return 1
            print_success(f"es.exe 路径已更新: {path}")
            _verify_es_runnable(path)
        else:
            if not _save_manual_path(everything_path=path):
                return 1
            print_success(f"Everything.exe 路径已更新: {path}")

        print_success(f"路径配置已保存到: {os.path.normpath(PATH_ENV_FILE)}")
        _print_current_config()
        print()
        print_header("🎉！！！配置成功！！！🎉")
        return 0


    if os.path.isfile(path):
        print_not_found(f"这不是 Everything.exe 或 es.exe: {path}")
        print_not_found("请输入正确的路径（Everything 安装目录，或 Everything.exe / es.exe 的完整路径）")
        return 1

    if not os.path.isdir(path):
        print_not_found(f"未找到该路径: {path}")
        print_not_found("请输入正确的路径")
        return 1

    print_info(f"目标: {path}")
    print_info("模式: 目录（同时更新 Everything.exe 与 es.exe 路径）")
    print()

    everything_exe = _lookup_in_dir(path, "Everything.exe")
    es_exe = _lookup_in_dir(path, "es.exe")

    missing = []
    if not everything_exe:
        missing.append("Everything.exe")
    if not es_exe:
        missing.append("es.exe")


    if not everything_exe and not es_exe:
        print_not_found(f"未找到 {' 和 '.join(missing)}（该目录下两者都不存在）")
        print_not_found("请输入正确的路径")
        print_info(f"已检索目录: {path}")
        return 1


    if not _save_manual_path(
        everything_path=everything_exe if everything_exe else None,
        es_path=es_exe if es_exe else None,
    ):
        return 1

    if everything_exe:
        print_success(f"Everything.exe 路径已更新: {everything_exe}")
    if es_exe:
        print_success(f"es.exe 路径已更新: {es_exe}")
        _verify_es_runnable(es_exe)
    print_success(f"路径配置已保存到: {os.path.normpath(PATH_ENV_FILE)}")

    if missing:
        print()
        print_not_found(f"未找到 {' 和 '.join(missing)}（该目录下不存在这{'两个' if len(missing) > 1 else '个'}文件）")
        print_not_found(f"请输入正确的路径，或单独指定 {missing[0]} 的完整路径后加 --install")
        _print_current_config()
        return 1

    _print_current_config()
    print()
    print_header("🎉！！！配置成功！！！🎉")
    return 0






def discover_and_configure(silent: bool = False) -> bool:
    

    existing_everything, existing_es = load_path_config()
    if existing_everything and existing_es:
        if verify_installation(existing_everything, existing_es, silent=silent):
            return True


    es_path = find_es_exe()
    if not es_path:
        return False

    everything_path = find_everything_exe()
    if not everything_path:
        everything_path = os.path.join(os.path.dirname(es_path), "Everything.exe")
        if not os.path.isfile(everything_path):
            everything_path = None
    save_path_config(everything_path, es_path, silent=silent)

    if verify_installation(everything_path, es_path, silent=silent):
        return True
    return False


def main():
    """命令行入口：无参数 → 自动发现；带路径 + --install → 手动配置"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Everything Search - 安装配置工具（自动发现 / 手动指定 es.exe 与 Everything.exe 路径）",
        epilog=(
            "示例:\n"
            "  python install.py                                             自动发现并配置\n"
            "  python install.py \"D:\\Everything1.4\" --install                目录：同时更新两者\n"
            "  python install.py \"D:\\Everything1.4\\es.exe\" --install         只更新 es.exe\n"
            "  python install.py \"D:\\Everything1.4\\Everything.exe\" --install 只更新 Everything"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", default=None,
                        help="Everything 安装目录，或 Everything.exe / es.exe 的完整路径（配合 --install）")
    parser.add_argument("--install", action="store_true",
                        help="把指定路径写入 path.env（目录=同时更新两者；单个 exe=只更新对应项）")

    args = parser.parse_args()

    if args.install or args.path:
        if args.path and not args.install:
            print_info("检测到路径参数，按 --install 手动配置模式处理")
        return install_from_path(args.path)

    return run_auto_discovery()


def run_auto_discovery():
    """自动发现流程（无参数运行 install.py 时的默认行为）"""
    print_header("Everything Search v1 - 安装配置工具")
    print("  此工具将自动发现 Everything 安装位置并配置 es.exe")
    print()


    existing_everything, existing_es = load_path_config()
    if existing_everything and existing_es:
        print_info("发现已有 path.env 配置:")
        print_info(f"  EVERYTHING_PATH = {existing_everything}")
        print_info(f"  ES_PATH = {existing_es}")
        print()


    if discover_and_configure(silent=False):
        print()
        print_header("🎉！！！配置成功！！！🎉")
        print("  现在可以使用 search_core.py 进行文件搜索:")
        print()
        print('    python search_core.py "*.pdf"')
        print('    python search_core.py "report"')
        print()
        return 0
    else:
        print()
        print_error("未能找到 es.exe")
        print_info("请先安装 Everything: https://www.voidtools.com/zh-cn/downloads/")
        print_info("并下载 es.exe: https://www.voidtools.com/zh-cn/downloads/#cli")
        print_info("若已安装到非常规目录，可手动指定路径:")
        print(r'       python install.py "D:\你的\Everything目录" --install')
        return 1


if __name__ == "__main__":
    sys.exit(main())
