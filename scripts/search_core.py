#!/usr/bin/env python3


from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import subprocess
import time
from collections import namedtuple
from datetime import datetime
from typing import Optional, List, Tuple


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from install import (
    find_es_exe,
    find_everything_exe,
    start_everything_background,
    save_path_config,
    discover_and_configure,
    install_from_path,
    read_env_dict,
    PATH_ENV_FILE,
)


def _log(msg: str) -> None:
    """运维日志：一律写 stderr，不污染 stdout 的结果流（表格或 JSON）"""
    print(msg, file=sys.stderr)





SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]



SORT_FIELD_MAP = {
    "name": "name",
    "path": "path",
    "size": "size",
    "ext": "extension",
    "extension": "extension",
    "date": "date-modified",
    "dm": "date-modified",
    "date-modified": "date-modified",
    "dc": "date-created",
    "date-created": "date-created",
    "da": "date-accessed",
    "date-accessed": "date-accessed",
    "rc": "run-count",
    "run-count": "run-count",
}


_MUSIC_EXT = {".flac", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".wma",
              ".mid", ".midi", ".opus", ".ape", ".alac", ".cda"}
_VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
              ".rmvb", ".ts", ".m2ts", ".vob", ".mpg", ".mpeg"}
_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
              ".svg", ".heic", ".ico", ".raw", ".cr2"}
_DOC_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
            ".md", ".rtf", ".odt", ".csv", ".epub", ".tex", ".wps", ".pages"}
_ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".bz2", ".xz", ".cab", ".lz"}



CATEGORY_ORDER = [
    ("music", "音乐", "🎵"),
    ("video", "视频", "🎬"),
    ("image", "图片", "📷"),
    ("doc", "文档", "📄"),
    ("archive", "压缩包", "📦"),
    ("other", "其他文件", "📎"),
    ("folder", "文件夹", "📁"),
]


def get_category(result: SearchResult) -> str:
    
    if result.item_type == "文件夹":
        return "folder"
    ext = result.extension.lower()
    if ext in _MUSIC_EXT:
        return "music"
    if ext in _VIDEO_EXT:
        return "video"
    if ext in _IMAGE_EXT:
        return "image"
    if ext in _DOC_EXT:
        return "doc"
    if ext in _ARCHIVE_EXT:
        return "archive"
    return "other"






def format_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的格式"""
    if size_bytes < 0:
        return "N/A"
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024.0 and unit_index < len(SIZE_UNITS) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{int(size)} B" if unit_index == 0 else f"{size:.1f} {SIZE_UNITS[unit_index]}"


def get_file_extension(filename: str) -> str:
    """获取文件扩展名（含点号）"""
    _, ext = os.path.splitext(filename)
    return ext







SearchResult = namedtuple("SearchResult", ["filename", "filepath", "size", "extension", "size_formatted", "item_type", "date_modified"])


def create_search_result(filename: str, filepath: str, size: int, item_type: str = "文件", date_modified: str = "") -> SearchResult:
    """创建 SearchResult 实例"""
    return SearchResult(
        filename=filename,
        filepath=filepath,
        size=size,
        extension=get_file_extension(filename),
        size_formatted=format_size(size),
        item_type=item_type,
        date_modified=date_modified
    )

def _decode_bytes(raw_bytes: bytes) -> str:
    
    for encoding in ("utf-8", "gbk", "cp1252", "shift-jis", "utf-16-le"):
        try:
            text = raw_bytes.decode(encoding)

            if any(c in text for c in ("Filename", "Name", "Error", "IPC")):
                return text
        except (UnicodeDecodeError, LookupError):
            continue

    return raw_bytes.decode("utf-8", errors="replace")


def parse_es_output(raw_bytes: bytes) -> List[SearchResult]:
    
    results = []
    output = _decode_bytes(raw_bytes).strip()
    if not output:
        return results




    rows = list(csv.reader(io.StringIO(output)))
    if not rows:
        return results

    data_rows = rows[1:] if rows[0] and rows[0][0].strip().lower() == "size" else rows

    for row in data_rows:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        size_str, date_modified, full = (row + ["", "", ""])[:3]
        full = full.strip()
        try:
            size = int(size_str.strip())
        except (ValueError, IndexError):
            size = 0

        filename = os.path.basename(full) or full
        item_type = "文件夹" if (full and os.path.isdir(full)) else "文件"
        results.append(create_search_result(filename, full, size, item_type, date_modified.strip()))

    return results


def search_files(query: str, max_results: int = 100, sort: Optional[str] = None, descending: bool = False) -> Tuple[List[SearchResult], Optional[str]]:
    
    es_path = find_es_exe()

    if not es_path:
        return [], "ES_EXE_NOT_FOUND"




    cmd = [es_path, "-csv", "-size", "-dm", "-max-results", str(max_results)]


    if sort:
        es_sort_col = SORT_FIELD_MAP.get(sort.lower())
        if es_sort_col is None:
            return [], f"🔴 不支持的排序字段: {sort}（可选: {', '.join(sorted(SORT_FIELD_MAP))}）"
        cmd += ["-sort", es_sort_col, "-sort-descending" if descending else "-sort-ascending"]


    cmd.append(query)

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode != 0:
            error_msg = _decode_bytes(result.stderr).strip()
            if "everything" in error_msg.lower() and ("not running" in error_msg.lower() or "ipc" in error_msg.lower()):
                return [], "EVERYTHING_NOT_RUNNING"
            return [], f"🔴 es.exe 报错 : {error_msg}"


        _save_current_paths_once()

        if not result.stdout.strip():
            return [], None

        results = parse_es_output(result.stdout)
        return results, None

    except subprocess.TimeoutExpired:
        return [], "🔴 搜索超时（30秒），请缩小搜索范围"
    except FileNotFoundError:
        return [], f"🔴 无法执行 es.exe: {es_path}"
    except Exception as e:
        return [], f"🔴 搜索异常: {str(e)}"







FILLER_WORDS = [
    "的", "得", "地",
    "帮我", "帮忙", "搜索", "查找", "查查",
    "帮一帮", "搜一搜", "找一找",
    "找一下", "搜一下", "查一查", "查一下",
    "一下", "找找",
    "有没有", "是不是", "在不在",
    "在哪", "在这", "在那", "哪里",
    "那个", "这个", "那首", "这首",
    "了", "吗", "呢", "吧", "啊", "呀", "嘛", "哈",
    "歌曲", "曲", "文件", "文件夹",
]


def split_query(query: str) -> List[str]:
    
    text = query.strip()


    for word in sorted(FILLER_WORDS, key=len, reverse=True):
        text = text.replace(word, " ")


    parts = re.split(r'[\s\-—–·|,，、/\\]+', text)


    keywords = []
    for part in parts:
        part = part.strip().strip('"\'')
        if not part:
            continue
        if len(part) < 2:
            continue
        keywords.append(part)

    return keywords


def _sort_results_locally(results: List[SearchResult], sort: str, descending: bool) -> List[SearchResult]:
    
    field = sort.lower()
    if field == "size":
        key = lambda r: r.size
    elif field in ("date", "dm", "date-modified", "dc", "date-created", "da", "date-accessed"):

        key = lambda r: _parse_date(r.date_modified) or datetime.min
    elif field == "path":
        key = lambda r: r.filepath.lower()
    elif field in ("ext", "extension"):
        key = lambda r: r.extension.lower()
    else:
        key = lambda r: r.filename.lower()
    return sorted(results, key=key, reverse=descending)


def _merge_new(seen_paths: set, collected: List[SearchResult], results: List[SearchResult]) -> int:
    """将 results 按 filepath 去重后未出现过的条目并入 collected，返回新增条数"""
    added = 0
    for r in results:
        if r.filepath not in seen_paths:
            seen_paths.add(r.filepath)
            collected.append(r)
            added += 1
    return added


def fallback_search(query: str, max_results: int = 100, sort: Optional[str] = None, descending: bool = False) -> Tuple[List[SearchResult], Optional[str], str, int]:
    
    keywords = split_query(query)

    if not keywords:
        return [], None, "", 0


    if len(keywords) == 1 and keywords[0] == query.strip() and len(keywords[0]) <= 2:
        return [], None, "", 0


    partial_results = []
    matched_tokens = []
    seen_paths = set()
    total_found = 0

    for kw in keywords:

        kw_results, kw_error = search_files(kw, max_results=20, sort=sort, descending=descending)
        if kw_error is None and kw_results:
            matched_tokens.append(kw)
            total_found += _merge_new(seen_paths, partial_results, kw_results)
            continue


        if len(kw) <= 2:
            continue

        substrings = sliding_window_substrings(kw)
        _log(f"   🔎 正在尝试子串匹配 {', '.join(f'\"{s}\"' for s in substrings[:8])}...")
        for sub in substrings:
            sub_results, sub_error = search_files(sub, max_results=10, sort=sort, descending=descending)
            if sub_error is None and sub_results:
                matched_tokens.append(sub)
                total_found += _merge_new(seen_paths, partial_results, sub_results)

    if partial_results:

        if sort:
            partial_results = _sort_results_locally(partial_results, sort, descending)

        partial_results = partial_results[:max_results]
        unique_tokens = list(dict.fromkeys(matched_tokens))
        desc = "部分匹配: " + ", ".join(f'"{t}"' for t in unique_tokens[:10])
        return partial_results, None, desc, total_found

    return [], None, "", 0


def sliding_window_substrings(keyword: str, max_calls: int = 15) -> List[str]:
    
    length = len(keyword)
    if length <= 2:
        return []

    substrings = []
    count = 0

    for win_size in range(length - 1, 1, -1):
        for start in range(length - win_size + 1):
            if count >= max_calls:
                return substrings
            substrings.append(keyword[start:start + win_size])
            count += 1

    return substrings






def _display_width(s: str) -> int:
    """计算字符串在终端的显示宽度（CJK/全角字符占 2 列，ASCII 占 1 列）"""
    w = 0
    for c in s:
        w += 2 if ord(c) > 127 else 1
    return w


def _pad_right(s: str, width: int) -> str:
    """按显示宽度左对齐填充"""
    return s + ' ' * max(0, width - _display_width(s))


def _pad_left(s: str, width: int) -> str:
    """按显示宽度右对齐填充"""
    return ' ' * max(0, width - _display_width(s)) + s


def _truncate_by_width(s: str, max_width: int, suffix: str = "..") -> str:
    """按显示宽度截断字符串，超出部分用 suffix 替代"""
    if _display_width(s) <= max_width:
        return s
    suffix_w = _display_width(suffix)
    if suffix_w >= max_width:
        return suffix[:max(1, max_width)] if max_width > 0 else ""
    target = max_width - suffix_w
    result = ""
    w = 0
    for c in s:
        cw = 2 if ord(c) > 127 else 1
        if w + cw > target:
            break
        result += c
        w += cw
    return result + suffix


def _parse_date(date_str: str) -> Optional[datetime]:
    
    s = date_str.strip()
    if not s:
        return None
    for fmt in (
        "%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M",
        "%d/%m/%Y %H:%M", "%d.%m.%Y %H:%M",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _format_date_display(date_str: str) -> str:
    """将日期字符串格式化为紧凑的 YYYY-MM-DD HH:MM 形式，解析失败原样返回"""
    dt = _parse_date(date_str)
    if dt is not None:
        return dt.strftime("%Y-%m-%d %H:%M")
    return date_str.strip()


def _display_type(result: SearchResult) -> str:
    
    if result.item_type == "文件夹":
        return "文件夹"
    if result.extension.lower() == ".lnk":
        return "快捷方式"
    return result.item_type


def _display_name(result: SearchResult) -> str:
    
    name = result.filename
    ext = result.extension
    if ext and name.lower().endswith(ext.lower()):
        return name[:-len(ext)]
    return name


def _display_dir(filepath: str) -> str:
    
    parent = os.path.dirname(filepath)
    if not parent:
        return filepath
    if not parent.endswith(("\\", "/")):
        parent += "\\" if os.sep == "\\" else os.sep
    return parent


def format_results_table(results: List[SearchResult]) -> str:
    
    if not results:
        return "🌫️ 未找到目标文件，请检查搜索词的有效性"

    MAX_NAME_W = 40
    MAX_PATH_W = 80


    name_displays = [_display_name(r) for r in results]
    date_displays = [_format_date_display(r.date_modified) for r in results]
    dir_displays = [_display_dir(r.filepath) for r in results]

    ext_displays = [
        "" if (r.item_type == "文件夹" or not r.extension) else r.extension
        for r in results
    ]

    show_ext = any(ext_displays)

    max_name = min(max([_display_width(n) for n in name_displays] + [_display_width("文件名")]), MAX_NAME_W)
    max_ext = max([_display_width(e) for e in ext_displays] + [_display_width("扩展名")]) if show_ext else 0
    max_size = max([_display_width(r.size_formatted) for r in results] + [_display_width("大小")])
    max_date = max([_display_width(d) for d in date_displays] + [_display_width("修改日期")])
    max_path = min(max([_display_width(d) for d in dir_displays] + [_display_width("路径")]), MAX_PATH_W)

    header_cols = [_pad_right("文件名", max_name)]
    if show_ext:
        header_cols.append(_pad_right("扩展名", max_ext))
    header_cols.append(_pad_left("大小", max_size))
    header_cols.append(_pad_right("修改日期", max_date))
    header_cols.append(_pad_right("路径", max_path))
    header = "  ".join(header_cols)

    col_widths = [max_name]
    if show_ext:
        col_widths.append(max_ext)
    col_widths += [max_size, max_date, max_path]
    separator = "-" * (sum(col_widths) + 2 * (len(col_widths) - 1))
    lines = [header, separator]

    for r, name_disp, ext_disp, date_disp, dir_disp in zip(
            results, name_displays, ext_displays, date_displays, dir_displays):
        name = _truncate_by_width(name_disp, max_name)
        path = _truncate_by_width(dir_disp, max_path)
        row = [_pad_right(name, max_name)]
        if show_ext:
            row.append(_pad_right(ext_disp, max_ext))
        row.append(_pad_left(r.size_formatted, max_size))
        row.append(_pad_right(date_disp, max_date))
        row.append(path)
        lines.append("  ".join(row))

    return "\n".join(lines)


def categorize(results: List[SearchResult]) -> List[Tuple[str, str, str, List[SearchResult]]]:
    
    buckets = {}
    for r in results:
        buckets.setdefault(get_category(r), []).append(r)
    return [(key, label, emoji, buckets[key]) for key, label, emoji in CATEGORY_ORDER if key in buckets]


def format_results_grouped(results: List[SearchResult]) -> str:
    
    if not results:
        return "🌫️ 未找到目标文件，请检查搜索词的有效性"

    sections = [f"🎊 共找到 {len(results)} 个结果，按类型列表如下 🎊", ""]
    for key, label, emoji, items in categorize(results):
        sections.append(f"{emoji} {label}（共 {len(items)} 个）")
        sections.append(format_results_table(items))
        sections.append("")
        sections.append("")

    return "\n".join(sections).rstrip()


def print_results(results: List[SearchResult]) -> None:
    """打印搜索结果（按类型分表，全部结果均显示，不截断）"""
    print(format_results_grouped(results))
    print()


def results_to_json_obj(
    results: List[SearchResult],
    query: str,
    fallback_desc: str = "",
    sort: Optional[str] = None,
    descending: bool = False,
) -> dict:
    

    cat_groups = categorize(results)
    groups = [
        {"category": key, "label": label, "emoji": emoji, "count": len(items)}
        for key, label, emoji, items in cat_groups
    ]



    ordered = [r for _, _, _, items in cat_groups for r in items]

    items = []
    for r in ordered:
        cat = get_category(r)
        items.append({
            "filename": _display_name(r),
            "extension": "" if r.item_type == "文件夹" else r.extension,
            "type": _display_type(r),
            "category": cat,
            "size": r.size,
            "size_formatted": r.size_formatted,
            "date_modified": _format_date_display(r.date_modified),
            "path": r.filepath,
            "directory": _display_dir(r.filepath),
        })


    matched_tokens: List[str] = []
    if fallback_desc:
        matched_tokens = re.findall(r'"([^"]+)"', fallback_desc)

    return {
        "query": query,
        "total": len(results),
        "fallback": {"used": bool(fallback_desc), "matched_tokens": matched_tokens},
        "sort": ({"field": sort, "descending": descending} if sort else None),
        "groups": groups,
        "results": items,
    }


def print_results_json(
    results: List[SearchResult],
    query: str,
    fallback_desc: str = "",
    sort: Optional[str] = None,
    descending: bool = False,
) -> None:
    """以 JSON 格式输出搜索结果到 stdout（--json 模式）"""
    obj = results_to_json_obj(results, query, fallback_desc, sort, descending)
    print(json.dumps(obj, ensure_ascii=False, indent=2))






def _present(query: str, max_results: int, sort: Optional[str], descending: bool,
             json_mode: bool, results: List[SearchResult]) -> int:
    """有结果直接输出；无结果进入拆词回退输出（消除 main_search 中重复的"三元"分支）"""
    if results:
        if json_mode:
            print_results_json(results, query, sort=sort, descending=descending)
        else:
            print_results(results)
        return 0
    return _try_fallback_or_report(query, max_results, sort, descending, json_mode)


def _try_fallback_or_report(query: str, max_results: int, sort: Optional[str] = None,
                            descending: bool = False, json_mode: bool = False) -> int:
    
    _log(f"🔍 精确搜索 \"{query}\" 失败，正在尝试拆词搜索...")
    fb_results, fb_error, fb_desc, total_found = fallback_search(query, max_results, sort=sort, descending=descending)
    if fb_error is None and fb_results:
        if json_mode:
            print_results_json(fb_results, query, fallback_desc=fb_desc, sort=sort, descending=descending)
        else:
            print(f"💡 {fb_desc}\n")
            print(format_results_grouped(fb_results))
            print()
        return 0

    if json_mode:
        print_results_json([], query, sort=sort, descending=descending)
    else:
        print_results([])
    return 1


def main_search(query: str, max_results: int = 100, sort: Optional[str] = None,
                descending: bool = False, json_mode: bool = False) -> int:
    
    if not query or not query.strip():
        _log("🔴 请提供有效的搜索词")
        return 2


    if sort and sort.lower() not in SORT_FIELD_MAP:
        _log(f"🔴 不支持的排序字段: {sort}（可选: {', '.join(sorted(SORT_FIELD_MAP))}）")
        return 2

    query = query.strip()


    _log(f"🔎 正在精确搜索 \"{query}\" 中，请稍等...")
    results, error = search_files(query, max_results, sort=sort, descending=descending)

    if error is None:
        return _present(query, max_results, sort, descending, json_mode, results)


    if error == "ES_EXE_NOT_FOUND":
        _log("🔵 未找到 es.exe，正试着自动配置 es.exe 路径...")
        if discover_and_configure(silent=True):
            _log("🟢 配置成功，重新搜索中...")
            results, error = search_files(query, max_results, sort=sort, descending=descending)
            if error is None:
                return _present(query, max_results, sort, descending, json_mode, results)
        else:
            _log("🔴 自动配置失败")
            _log("   请手动运行 install.py 进行配置")
            _log("   或访问 https://www.voidtools.com/zh-cn/downloads/ 下载 Everything")
            return 2


    if error == "EVERYTHING_NOT_RUNNING":
        _log("🟠 Everything 未运行，正试着后台启动...")
        if start_everything_background():
            for _attempt in range(6):
                time.sleep(0.5)
                if _attempt == 2:
                    _log("   ⏳ 索引加载中，再等一下...")
                results, error = search_files(query, max_results, sort=sort, descending=descending)
                if error != "EVERYTHING_NOT_RUNNING":
                    break
            if error is None:
                return _present(query, max_results, sort, descending, json_mode, results)
            if error == "EVERYTHING_NOT_RUNNING":
                _log("🔴 Everything 已启动但 IPC 窗口未就绪（索引可能正在构建）")
                _log("   请稍后重试，或手动打开 Everything 等待索引完成")
            else:
                _log(error)
            return 2
        _log("🔴 无法自动启动 Everything")
        _log("   请手动启动 Everything 或运行 install.py 进行配置")
        _log("   ⬇️ 下载地址: https://www.voidtools.com/zh-cn/downloads/")
        return 2


    _log(error)
    return 2


_paths_saved = False


def _save_current_paths_once() -> None:
    
    global _paths_saved
    if _paths_saved:
        return
    es_path = find_es_exe()
    if es_path:
        everything_path = find_everything_exe() or os.path.join(os.path.dirname(es_path), "Everything.exe")
        before = read_env_dict()
        if save_path_config(everything_path, es_path, silent=True):
            if read_env_dict() != before:
                _log(f"  ✅ 路径配置已保存到: {os.path.normpath(PATH_ENV_FILE)}")
        _paths_saved = True






def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="search_core.py",
        description="Everything Search v1 - Windows 本地文件极速检索（基于 es.exe）",
        epilog=(
            "搜索语法参考: https://www.voidtools.com/support/everything/searching/\n"
            "\n"
            "手动配置路径 (--install):\n"
            "  python search_core.py \"D:\\Everything1.4\" --install                 目录：同时更新两者\n"
            "  python search_core.py \"D:\\Everything1.4\\es.exe\" --install          只更新 es.exe\n"
            "  python search_core.py \"D:\\Everything1.4\\Everything.exe\" --install  只更新 Everything"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="?", default=None,
                        help="搜索关键词（支持 Everything 搜索语法，如 *.pdf / ext:docx;pdf / size:>100mb）；"
                             "配合 --install 时表示 Everything 安装目录或 exe 完整路径")
    parser.add_argument("max_results", nargs="?", type=int, default=100, help="最大返回结果数（默认 100）")
    parser.add_argument("--sort", metavar="字段", default=None,
                        help=f"排序字段: {', '.join(sorted(SORT_FIELD_MAP))}")
    parser.add_argument("--desc", action="store_true", help="降序（配合 --sort 使用）")
    parser.add_argument("--asc", action="store_true", help="升序（默认，配合 --sort 使用）")
    parser.add_argument("--json", action="store_true",
                        help="以 JSON 格式输出结果到 stdout（运维日志走 stderr），便于智能体/脚本解析")
    parser.add_argument("--install", action="store_true",
                        help="把第一个位置参数当作路径写入 path.env（目录=同时更新 Everything.exe 与 es.exe；"
                             "单个 exe=只更新对应项），不执行搜索")

    args = parser.parse_args()


    if args.install:
        return install_from_path(args.query)

    if not args.query:
        parser.error("缺少搜索关键词（或使用 --install 配合路径进行手动配置）")

    descending = args.desc and not args.asc

    return main_search(args.query, args.max_results, sort=args.sort, descending=descending, json_mode=args.json)


if __name__ == "__main__":
    sys.exit(main())
