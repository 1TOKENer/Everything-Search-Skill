"""
test_search_core.py
===================
Everything Search v1 — search_core.py 单元测试

覆盖范围：
  - format_size()          : 字节格式化，含边界值
  - get_file_extension()   : 扩展名提取
  - create_search_result() : 结果对象构造
  - _decode_bytes()        : 多编码解码链
  - parse_es_output()      : CSV 解析（含空格/逗号/中文/空输出）
  - _display_width()       : CJK 显示宽度
  - _pad_right/_pad_left() : 宽度对齐填充
  - _truncate_by_width()   : 按宽度截断
  - format_results_table() : 表格格式化（空列表/单行/多行）
  - search_files()         : mock subprocess 调用
"""

import pytest
from unittest.mock import patch, MagicMock
from collections import namedtuple

import search_core
from search_core import (
    format_size,
    get_file_extension,
    create_search_result,
    SearchResult,
    _decode_bytes,
    parse_es_output,
    _display_width,
    _pad_right,
    _pad_left,
    _truncate_by_width,
    format_results_table,
    search_files,
)


# ============================================================
# format_size
# ============================================================

class TestFormatSize:
    """字节 → 人类可读格式转换"""

    @pytest.mark.parametrize("bytes_in, expected", [
        (0, "0 B"),
        (1, "1 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),          # 1 MB
        (1572864, "1.5 MB"),          # 1.5 MB
        (1073741824, "1.0 GB"),       # 1 GB
        (1099511627776, "1.0 TB"),    # 1 TB
    ])
    def test_normal_values(self, bytes_in, expected):
        assert format_size(bytes_in) == expected

    def test_negative_returns_na(self):
        assert format_size(-1) == "N/A"
        assert format_size(-1024) == "N/A"

    def test_large_value_caps_at_tb(self):
        """超过 TB 的值不应越界"""
        result = format_size(1099511627776 * 5)  # 5 TB
        assert "TB" in result

    def test_boundary_1023_bytes(self):
        """刚好低于 1KB 的值应保持 B 单位"""
        assert format_size(1023) == "1023 B"

    def test_boundary_1024_bytes(self):
        """恰好 1KB"""
        assert format_size(1024) == "1.0 KB"


# ============================================================
# get_file_extension
# ============================================================

class TestGetFileExtension:
    """文件扩展名提取"""

    @pytest.mark.parametrize("filename, expected", [
        ("report.pdf", ".pdf"),
        ("archive.tar.gz", ".gz"),
        ("README", ""),
        ("README.md", ".md"),
        (".gitignore", ""),              # 点文件 → os.path.splitext 返回 ('.gitignore', '')
        ("file.", "."),                  # 尾部点号 → ext 为 '.'
        ("no_ext", ""),
        ("UPPER.PDF", ".PDF"),
        ("mixed.CsV", ".CsV"),
    ])
    def test_extensions(self, filename, expected):
        assert get_file_extension(filename) == expected


# ============================================================
# create_search_result
# ============================================================

class TestCreateSearchResult:
    """SearchResult 对象构造"""

    def test_basic_creation(self):
        r = create_search_result("doc.pdf", r"C:\files\doc.pdf", 2048)
        assert r.filename == "doc.pdf"
        assert r.filepath == r"C:\files\doc.pdf"
        assert r.size == 2048
        assert r.extension == ".pdf"
        assert r.size_formatted == "2.0 KB"

    def test_zero_size(self):
        r = create_search_result("empty.txt", r"C:\empty.txt", 0)
        assert r.size == 0
        assert r.size_formatted == "0 B"

    def test_no_extension(self):
        r = create_search_result("Makefile", r"C:\proj\Makefile", 512)
        assert r.extension == ""

    def test_namedtuple_fields(self):
        """验证 SearchResult 是 namedtuple 且字段顺序正确"""
        assert SearchResult._fields == ("filename", "filepath", "size", "extension", "size_formatted")


# ============================================================
# _decode_bytes
# ============================================================

class TestDecodeBytes:
    """多编码解码链测试"""

    def test_utf8(self):
        raw = "Filename,Path,Size\n".encode("utf-8")
        assert "Filename" in _decode_bytes(raw)

    def test_gbk(self):
        """GBK 编码 — 需包含可辨认关键词（_decode_bytes 依赖关键词识别）"""
        raw = "Name,文件名\n".encode("gbk")
        result = _decode_bytes(raw)
        assert "Name" in result

    def test_cp1252(self):
        raw = "Filename,Path,Size\n".encode("cp1252")
        assert "Filename" in _decode_bytes(raw)

    def test_shift_jis(self):
        """Shift-JIS 编码 — 需包含可辨认关键词"""
        raw = "Name,名前\n".encode("shift-jis")
        result = _decode_bytes(raw)
        assert "Name" in result

    def test_empty_bytes(self):
        """空字节 → utf-8 replace 回退（不崩溃）"""
        assert _decode_bytes(b"") == ""

    def test_invalid_bytes_fallback(self):
        """无法被任何编码识别的字节 → utf-8 replace 回退"""
        raw = b"\xff\xfe\x00\x41"  # 混乱字节
        result = _decode_bytes(raw)
        # 不崩溃，返回字符串
        assert isinstance(result, str)

    def test_utf16_le(self):
        raw = "Filename".encode("utf-16-le")
        result = _decode_bytes(raw)
        assert "Filename" in result

    def test_error_keyword_recognized(self):
        """含 Error 关键字的输出应被正确识别"""
        raw = b"Error: Everything not running"
        assert "Error" in _decode_bytes(raw)


# ============================================================
# parse_es_output
# ============================================================

class TestParseEsOutput:
    """es.exe CSV 输出解析"""

    def test_empty_output(self):
        assert parse_es_output(b"") == []

    def test_whitespace_only(self):
        assert parse_es_output(b"   \n  ") == []

    def test_header_only_no_data(self):
        raw = b'Filename,Path,Size\n'
        assert parse_es_output(raw) == []

    def test_single_row(self):
        raw = b'Filename,Path,Size\nfile.txt,C:\\dir\\file.txt,1024\n'
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].filename == "file.txt"
        assert results[0].filepath == "C:\\dir\\file.txt"
        assert results[0].size == 1024
        assert results[0].extension == ".txt"
        assert results[0].size_formatted == "1.0 KB"

    def test_multiple_rows(self):
        raw = (
            b'Filename,Path,Size\n'
            b'a.txt,C:\\a.txt,100\n'
            b'b.pdf,D:\\docs\\b.pdf,2048\n'
            b'c.zip,E:\\backup\\c.zip,5242880\n'
        )
        results = parse_es_output(raw)
        assert len(results) == 3
        assert results[0].filename == "a.txt"
        assert results[1].filename == "b.pdf"
        assert results[2].filename == "c.zip"

    def test_filename_with_spaces(self):
        """含空格的文件名（CSV 引号包裹）"""
        raw = b'Filename,Path,Size\n"My Report.pdf","C:\\My Documents\\My Report.pdf",5120\n'
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].filename == "My Report.pdf"
        assert results[0].filepath == "C:\\My Documents\\My Report.pdf"

    def test_filename_with_comma(self):
        """含逗号的文件名（CSV 引号转义）"""
        raw = b'Filename,Path,Size\n"report,final.pdf","C:\\report,final.pdf",256\n'
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].filename == "report,final.pdf"

    def test_chinese_filename_gbk(self):
        """中文文件名 GBK 编码"""
        header = "Filename,Path,Size\n"
        row = "报告.pdf,C:\\文档\\报告.pdf,4096\n"
        raw = (header + row).encode("gbk")
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].filename == "报告.pdf"
        assert results[0].size == 4096

    def test_non_numeric_size_defaults_to_zero(self):
        raw = b'Filename,Path,Size\nfile.txt,C:\\file.txt,N/A\n'
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].size == 0

    def test_empty_size_defaults_to_zero(self):
        raw = b'Filename,Path,Size\nfile.txt,C:\\file.txt,\n'
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].size == 0

    def test_chinese_headers(self):
        """中文表头（文件名/路径/大小）"""
        header = "文件名,路径,大小\n"
        row = "测试.txt,C:\\测试.txt,256\n"
        raw = (header + row).encode("utf-8")
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].filename == "测试.txt"
        assert results[0].size == 256

    def test_name_column_alias(self):
        """表头使用 Name 而非 Filename"""
        raw = b'Name,Path,Size\ndoc.txt,C:\\doc.txt,512\n'
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].filename == "doc.txt"

    def test_empty_row_skipped(self):
        raw = b'Filename,Path,Size\n,,\nfile.txt,C:\\file.txt,100\n'
        results = parse_es_output(raw)
        # 第一行全空应被跳过
        assert len(results) == 1
        assert results[0].filename == "file.txt"

    def test_filename_empty_uses_path_basename(self):
        """文件名为空时从路径提取"""
        raw = b'Filename,Path,Size\n,C:\\dir\\derived.txt,100\n'
        results = parse_es_output(raw)
        assert len(results) == 1
        assert results[0].filename == "derived.txt"


# ============================================================
# _display_width
# ============================================================

class TestDisplayWidth:
    """CJK 显示宽度计算"""

    @pytest.mark.parametrize("text, expected", [
        ("", 0),
        ("a", 1),
        ("abc", 3),
        ("中", 2),
        ("中文", 4),
        ("a中", 3),                  # 1 + 2
        ("a中b文c", 7),              # 1+2+1+2+1
        ("日本語", 6),               # 3 个 CJK = 6
        ("hello世界", 9),             # 5 + 2 + 2
        ("🎉", 2),                    # emoji — ord > 127 → 实现判 > 127 → 2
    ])
    def test_widths(self, text, expected):
        assert _display_width(text) == expected


# ============================================================
# _pad_right / _pad_left
# ============================================================

class TestPadding:
    """宽度对齐填充"""

    def test_pad_right_ascii(self):
        assert _pad_right("ab", 5) == "ab   "

    def test_pad_right_cjk(self):
        result = _pad_right("中", 5)
        assert _display_width(result) == 5
        assert result == "中   "  # 2 + 3 spaces

    def test_pad_right_already_wide_enough(self):
        """字符串宽度 >= 目标宽度时不填充"""
        assert _pad_right("abcde", 3) == "abcde"

    def test_pad_right_zero_width(self):
        assert _pad_right("ab", 0) == "ab"

    def test_pad_left_ascii(self):
        assert _pad_left("ab", 5) == "   ab"

    def test_pad_left_cjk(self):
        result = _pad_left("中", 5)
        assert _display_width(result) == 5
        assert result == "   中"

    def test_pad_left_already_wide_enough(self):
        assert _pad_left("abcde", 3) == "abcde"


# ============================================================
# _truncate_by_width
# ============================================================

class TestTruncateByWidth:
    """按显示宽度截断"""

    def test_no_truncation_needed(self):
        assert _truncate_by_width("abc", 10) == "abc"

    def test_exact_fit(self):
        assert _truncate_by_width("abc", 3) == "abc"

    def test_truncate_ascii(self):
        result = _truncate_by_width("abcdef", 4)
        assert _display_width(result) <= 4
        assert result.endswith("..")
        assert result == "ab.."  # 2 chars + ".."

    def test_truncate_cjk(self):
        result = _truncate_by_width("中文测试", 4)
        assert _display_width(result) <= 4
        assert result.endswith("..")

    def test_truncate_mixed(self):
        result = _truncate_by_width("a中b文c", 3)
        assert _display_width(result) <= 3

    def test_suffix_wider_than_max(self):
        """suffix 本身比 max_width 宽时返回截断的 suffix"""
        result = _truncate_by_width("abcde", 2, suffix="...")
        # suffix_w(3) >= max_width(2) → return suffix[:max(1,2)] = ".."
        assert _display_width(result) <= 2

    def test_max_width_zero(self):
        assert _truncate_by_width("abc", 0) == ""

    def test_empty_string(self):
        assert _truncate_by_width("", 10) == ""


# ============================================================
# format_results_table
# ============================================================

class TestFormatResultsTable:
    """表格格式化输出"""

    def test_empty_results_returns_message(self):
        result = format_results_table([])
        assert "未找到" in result

    def test_single_result_contains_filename(self):
        r = create_search_result("doc.pdf", r"C:\docs\doc.pdf", 1024)
        table = format_results_table([r])
        assert "doc.pdf" in table
        assert ".pdf" in table
        assert "1.0 KB" in table

    def test_multiple_results_all_present(self):
        results = [
            create_search_result("a.txt", r"C:\a.txt", 100),
            create_search_result("b.pdf", r"D:\b.pdf", 2048),
        ]
        table = format_results_table(results)
        assert "a.txt" in table
        assert "b.pdf" in table

    def test_table_has_header_and_separator(self):
        r = create_search_result("doc.pdf", r"C:\doc.pdf", 512)
        table = format_results_table([r])
        lines = table.strip().split("\n")
        # 至少有表头、分隔线、数据行
        assert len(lines) >= 3
        # 分隔线应为连续的 -
        assert set(lines[1]) == {"-"}

    def test_long_filename_truncated(self):
        long_name = "a" * 100 + ".txt"
        r = create_search_result(long_name, "C:\\" + long_name, 100)
        table = format_results_table([r])
        # 表格中不应出现完整的 100+ 字符文件名
        assert long_name not in table


# ============================================================
# search_files (mock subprocess)
# ============================================================

class TestSearchFiles:
    """search_files() — 通过 mock subprocess 测试"""

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_successful_search(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b'Filename,Path,Size\ntest.txt,C:\\test.txt,1024\n',
            stderr=b""
        )
        results, error = search_files("test")
        assert error is None
        assert len(results) == 1
        assert results[0].filename == "test.txt"

    @patch("search_core.find_es_exe", return_value=None)
    def test_es_not_found(self, mock_find):
        results, error = search_files("test")
        assert results == []
        assert error == "ES_EXE_NOT_FOUND"

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_no_results(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"",
            stderr=b""
        )
        results, error = search_files("nonexistent")
        assert results == []
        assert error is None

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_everything_not_running(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=b"",
            stderr=b"Error: Everything IPC window not found. Is Everything running?"
        )
        results, error = search_files("test")
        assert results == []
        assert error == "EVERYTHING_NOT_RUNNING"

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_other_error(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=b"",
            stderr=b"Some other error"
        )
        results, error = search_files("test")
        assert results == []
        assert "Some other error" in error

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_timeout(self, mock_run, mock_find):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="es.exe", timeout=30)
        results, error = search_files("test")
        assert results == []
        assert "超时" in error

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_filenotfound_exception(self, mock_run, mock_find):
        mock_run.side_effect = FileNotFoundError()
        results, error = search_files("test")
        assert results == []
        assert "es.exe" in error

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_generic_exception(self, mock_run, mock_find):
        mock_run.side_effect = RuntimeError("Unexpected")
        results, error = search_files("test")
        assert results == []
        assert "Unexpected" in error

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_max_results_passed_to_command(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"", stderr=b""
        )
        search_files("test", max_results=50)
        cmd = mock_run.call_args[0][0]
        assert "50" in cmd
        assert "-max-results" in cmd

    @patch("search_core.find_es_exe", return_value=r"C:\Everything\es.exe")
    @patch("search_core.subprocess.run")
    def test_csv_flag_in_command(self, mock_run, mock_find):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"", stderr=b""
        )
        search_files("test")
        cmd = mock_run.call_args[0][0]
        assert "-csv" in cmd
        assert "-size" in cmd
