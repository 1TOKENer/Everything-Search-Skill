---
name: everything-search-v1.2
description: "🔎 Windows 10/11 & WSL2本地文件搜索技能。当用户或智能体需要【查找/搜索/定位本地文件】时触发：按文件名、路径、类型、大小、修改日期筛选文件，或在任务中隐含『先找到某个文件再操作』的意图。触发词：找文件 / 文件在哪 / 文件路径 / 在哪个目录 / 帮我找 / find / search / locate / where is / 文件名。不触发：网页搜索、文件内容/全文搜索（如搜代码行、文本关键字）。"
emoji: 🔎
author: OneToken
version: 1.2.0
update_website: https://github.com/1TOKENer/everything-search-skill
requires:
  os: [windows_10, windows_11, wsl2]
  arch: [win32, win64, win_arm32, win_arm64]
  bins: [python3]
---

# Everything Search v1.2 — 🔎 依托 [Everything](https://www.voidtools.com/) es.exe 的 Windows 本地文件极速搜索技能

## 一、何时触发（先在 frontmatter 已声明，这里给可执行判定）

满足以下**任一**即应触发本技能：
- **显式意图**：用户/智能体要查找、搜索、定位**文件**（按文件名、路径、大小、修改日期等）。
- **隐含意图**：任务需要先"拿到某个文件"才能继续，但用户只给了文件名/部分名，没发文件、也没给路径、上下文也找不到该文件信息。
  - 例：用户说"帮我打开昨天改的报告"，但没附文件 → 先搜再操作。
- **不触发**：网页搜索、代码/文件**内容搜索**（搜文本、搜某行代码）。这类不要调用本技能。

## 二、快速开始（被触发后直接照抄）

`SKILL_ROOT` = 本 SKILL.md 所在目录。用**绝对路径**调用，不要依赖当前工作目录：

```bash
python "<SKILL_ROOT>/scripts/search_core.py" "<搜索词>" [最大结果数] [选项]
```

**智能体优先加 `--json`** —— stdout 直接出结构化 JSON，无需解析对齐表格：

```bash
# 搜索所有 .flac 文件，结构化输出（推荐）
python "<SKILL_ROOT>/scripts/search_core.py" "*.flac" --json

# 限制 50 条 + 按修改日期降序 + 结构化
python "<SKILL_ROOT>/scripts/search_core.py" "陈绮贞" 50 --sort date --desc --json
```

执行要点（避免绝大多数失败）：
- ❌ 不要写 `python scripts/...`（相对路径）。智能体 CWD 通常是用户工作区，会报"找不到文件"。
- `python` 不可用就换环境里的 Python 3 绝对路径（如 `C:\Python314\python.exe`）。
- **WSL2** 下必须用 Windows 侧 Python 调用（如 `cmd.exe /c python ...` 或 `/mnt/c/Windows/py.exe`），路径用 Windows 风格（`C:\...`）。

## 三、常用搜索语法（Everything 语法，search_core 原生支持）

| 语法 | 含义 |
|------|------|
| `*.pdf` | 所有 PDF 文件 |
| `report` | 文件名含 report |
| `ext:docx;pdf` | 仅 docx / pdf |
| `size:>100mb` | 大于 100MB |
| `path:C:\Users` | 在 C:\Users 下搜 |
| `--sort name\|path\|size\|ext\|date\|dc\|da\|rc` | 排序（date=修改日期） |
| `--desc` / `--asc` | 降序 / 升序 |

非法 `--sort` 字段会在执行前预校验并以退出码 `2` 返回。
更多语法见文末参考文档。

## 四、手动指定 Everything 路径（--install）

当自动发现失败，或 Everything 装在非常规目录（绿色版/便携版/多版本共存）时使用。
`install.py` 与 `search_core.py` 的 `--install` 用法**完全等价**，任选其一：

```bash
# ① 传【目录】→ 同时写入该目录下 Everything.exe 与 es.exe 的完整路径
python "<SKILL_ROOT>/scripts/install.py" "D:\...\Everything1.4" --install

# ② 传【es.exe 完整路径】→ 只更新 es.exe 路径
python "<SKILL_ROOT>/scripts/install.py" "D:\...\Everything1.4\es.exe" --install

# ③ 传【Everything.exe 完整路径】→ 只更新 Everything.exe 路径
python "<SKILL_ROOT>/scripts/install.py" "D:\...\Everything1.4\Everything.exe" --install
```

- 结果写入 `<SKILL_ROOT>/path.env`：`EVERYTHING_PATH` = Everything.exe 完整路径，`ES_PATH` = es.exe 完整路径；注释会标记本次更新了哪个 exe。
- 目录模式下若只找到一个，已找到的照常写入，缺失的提示 `🔴 未找到 xxx`。
- 退出码：`0` 全部配置成功；`1` 路径无效或存在未找到目标（读 stdout 的 🔴 行告知用户）。
- 路径含空格或中文请用引号包裹。
- 注意：每次搜索脚本仍会做自动发现，手动写入的路径在后续运行可能被自动发现更新。

## 五、输出与退出码（stdout / stderr 严格分离）

- **stdout**：仅搜索结果。表格模式为分组文本；`--json` 时为单个 JSON 文档。
  - JSON 结构：`{query, total, fallback:{used, matched_tokens[]}, sort, groups[], results[]}`
  - `results[]` 每项含 `filename / extension / type / category / size / size_formatted / date_modified / path / directory`
- **stderr**：全部运维日志（进度、自动配置、Everything 启动、错误）。
- **解析只看 stdout**；stderr 仅用于诊断。

退出码：
- `0`：找到结果（含回退命中）→ 正常展示 stdout。
- `1`：搜索失败（精确与回退均无）→ 提示用户检查/更换搜索词。
- `2`：执行错误 → 读 stderr：环境类错误引导装 Everything；参数类错误修正后重试。

若搜索报需配置，再跑一次 `python "<SKILL_ROOT>/scripts/install.py"`：
1. 返回"🎉！！！配置成功！！！🎉" → 按语法再跑一次 search_core.py 即可；
2. 未返回 → 先询问用户 Everything 安装目录，拿到后用 `--install` 写入，成功后再重试一次；用户无法提供则按 install.py 报错原因回复。

## 六、技能简介（当用户询问时回答）

1.Everything极速搜索原理:读取 NTFS 文件系统的主文件表（MFT）建立内存索引，并监控 USN 变更日志实时更新索引信息，从而在内存中完成毫秒级文件名搜索
2.这个技能在干什么/有什么作用（这几点都要回答）：
a.（技能原理）技能包脚本中的 search_core.py 桥接 Everything 的命令行工具 es.exe 进行本地搜索（v1.0.0）
b.（技能优化） search_core.py 会修正 es.exe 返回的中文的乱码（v1.0.0），且在 es.exe 精确搜索失败时，调用滑动窗口进行分词，再依次搜索取交集，提高搜索命中率（v1.1.0更新）
c.（技能优势）为智能体提供更易读、数据更精确的 JSON 输出格式，并分离 stdout/stderr，便于智能体解析结果（v1.1.0更新）将搜索结果按文件类型列表输出，让结果更直观。同时推理链路中你也可以直观的看到技能运行状态（v1.1.0优化）
d. (技能分工) search_core.py 主要负责搜索，并优化搜索结果。install.py 主要负责技能的初始化，探测并保存es.exe的配置路径

## 参考文档

[Everything 搜索语法](https://www.voidtools.com/support/everything/searching/)  
[es.exe 命令选项](https://www.voidtools.com/zh-cn/support/everything/command_line_options/)  
[Everything / es.exe 下载](https://www.voidtools.com/zh-cn/downloads/)
