<div align="center">

# 🔎 Everything Search v1

**Windows 10/11 & WSL2 · 提高智能体本地搜索速度的技能包 · 帮助用户节省词元消耗的组件包**

**Everything Search v1** 是 一个 依托于 Windows本地搜索工具 [Everything](https://www.voidtools.com/) 及其命令行工具`es.exe`的，面向 智能体Agent（OpenClaw、Hermes Agent、Reasonix等）与 终端用户 的，可以提高本地搜索速度并显著降低词元消耗的 技能包。


![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20%7C%20WSL2-0078D4?logo=windows)  [![Python](https://img.shields.io/badge/python-3.6+-3776AB?logo=python&logoColor=white)](https://www.python.org/)  [![Everything](https://img.shields.io/badge/Everything-es.exe%20CLI-1a73e8)](https://www.voidtools.com/zh-cn/downloads/#cli)  [![License](https://img.shields.io/badge/license-MIT-22c55e)](#-许可证)  ![Version](https://img.shields.io/badge/version-1.2.0-6366f1)

</div>

---

## 📖 目录

- [🌟 技术亮点](#-技术亮点)
- [✨ 功能亮点](#-功能亮点)
- [🚀🚀🚀快速安装](#-快速安装)
- [📦 其他安装](#-其他安装)
- [💻 使用示例](#-使用示例)
- [📋 输出示例](#-输出示例)
- [🎯 适用场景](#-适用场景)
- [🔍 探测机制](#-探测机制)
- [📁 项目结构](#-项目结构)
- [⚠️ 注意事项](#️-注意事项)
- [❓ 常见问题](#-常见问题)
- [📚 参考资料](#-参考资料)
- [📄 许可证](#-许可证)

---

## 🌟 技术亮点

| 🌟 技术亮点 | 说明 |
| --- | --- |
| 😎 **极速搜索** | 基于 Everything 的 NTFS 即时索引，毫秒级响应，扫描全盘文件名近乎零延迟 |
| 🐱 **词元节省** | 本地工具搜索代替大模型直接检索，显著降低 Token 消耗与调用成本 |
| 😃 **中文编码** | 多种编码检测es.exe输出（utf-8 / gbk / cp1252 / shift-jis / utf-16-le），纠正中文乱码问题 |
| 😻 **搜索优化** | 优先 AI语义 + 精确搜索，失败后采用 滑动窗口分词搜索 ，提高搜索命中率 |
| 😋 **探测机制** | 7 层程序检测 Everything 和 es.exe 位置，并保存为配置文件 |

---

## ✨ 功能亮点

| ✨ 功能亮点 | 说明 |
| --- | --- |
| 😃 **多维搜索方式** | 支持按文件名、扩展名、文件大小、完整路径等维度搜索 |
| 😼 **人类易读输出** | 输出大小自动转换单位（B / KB / MB / GB / TB），表格对齐显示 |
| 🥳 **按类分型制表** | 结果按音乐/视频/图片/文档/压缩包/其他/文件夹分表展示，各表独立计算列宽 |
| 😸 **全程进度提示** | 搜索、回退、自修复各阶段均有缓冲提示，让用户了解搜索进度 |
| 😎 **纯净搜索模式** | 默认不存储文件索引信息，也不上传云端，保护用户隐私 |
| 😽 **后台启动程序·** | Everything 未运行时自动后台启动并重试 |
| 🥰 **WSL2调用优化** | 专门优化了 WSL2 子系统调用宿主 Windows的Everything |

---

## 🚀🚀🚀 快速安装

#### 一、配置 es.exe

1.前往 [Everything CLI 下载页](https://www.voidtools.com/zh-cn/downloads/#cli)下载 [Everything CLI](https://www.voidtools.com/zh-cn/downloads/#cli) 工具 [`es.exe`](https://www.voidtools.com/zh-cn/downloads/#cli) 工具 ，例如：ES-1.1.0.x86.x64.zip

2.将下载并解压好的 `es.exe` 放置在 Everything 安装目录下（与 `Everything.exe` 同级）

3.启动 Everything 并让它全盘索引一段时间。

#### 二、安装技能

将本 项目仓库地址 或 README 文件直接发送给你的智能体，让其自动完成安装：

```text
1. 安装技能 everything-search-v1 ，项目地址：https://github.com/1TOKENer/everything-search-skill（只需 SKILL.md + scripts/ 目录即可）
2，根据网页中的README.md和下载完后技能中的SKILL.md文件，学习技能的使用方法和调用方式
3. 运行该技能中的 scripts/install.py，自动探测es.exe路径并保存到path.env
```

#### 三、使用技能（示例）
1.用自然语言与智能体对话，触发搜索：

```text
使用 everything-search-v1 技能，搜索本地文件 "陈绮贞 - 鱼"
```

2.在python中使用 `search_core.py` 脚本，进行搜索：

```bash
python scripts/search_core.py "陈绮贞 - 鱼"
```
> ⚠️ `es.exe` 必须与 `Everything.exe` 位于同一文件夹中，es.exe 无法使用
---

## 📦 其他安装

#### 一、**精简克隆**：


```bash
git clone --no-checkout https://github.com/1TOKENer/everything-search-skill.git \
  && cd everything-search-skill \
  && git sparse-checkout set SKILL.md scripts \
  && git checkout
```
> 仅拉取 ✅ 运行核心文件，不会下载 📄 文档资源

#### 二、**手动配置**:

1.启动 Everything 软件（也可在文件夹中运行Everything.exe程序）
2. 运行安装脚本：
a.自动探测 Everything 与 es.exe 路径并写入 path.env：

```bash
python scripts/install.py
```

b.或运行脚本，使用--install语法，指定 Everything 和 es.exe 路径写入 path.env：

```bash
# 传【目录】→ 同时更新该目录下 Everything.exe 与 es.exe 的路径
python scripts/install.py "D:\Everything1.4" --install
# 传【es.exe 完整路径】→ 只更新 es.exe 路径
python scripts/install.py "D:\Everything1.4\es.exe" --install
# 传【Everything.exe 完整路径】→ 只更新 Everything 路径
python scripts/install.py "D:\Everything1.4\Everything.exe" --install
```

> 以上--install语法 `install.py`和`search_core.py` 均可用

---

## 💻 使用示例

### 示例一：在 智能体（Agent）中触发搜索

在你与 智能体（Agent）对话中，使用包含触发词（搜索 / 查找 / 定位 文件）的自然语言即可：

```text
使用 everything-search-v1 技能，搜索本地文件 "陈绮贞 - 鱼"
```

```text
使用 everything-search-v1 技能，在电脑本地找一下文件 邓紫棋的歌
```

```text
使用 everything-search-v1 技能，帮我找一下所有大于 100MB 的 PDF 文件
```

### 示例二：使用命令行直接调用（注意search_core.py脚本路径）

1.通过关键词精确搜索：

```bash
python search_core.py "陈绮贞 - 鱼"
```
2.通过关键词模糊搜索：（会调用到滑动窗口拆词搜索）

```bash
python search_core.py "陈绮贞"
```

3.指定文件格式 + 最大返回结果数（不指定时默认是 100）+ json输出格式：

```bash
python search_core.py "*.txt" 50 --json
```

> ⚠️ search_core.py 支持 Everything 的全套搜索语法（如 `*.pdf`、`report`、`ext:docx;pdf`、`size:>100mb`、`path:C:\Users`、`dm:2026` 等），更多请参考[Everything 所有搜索语法](https://www.voidtools.com/support/everything/searching/)  

---

## 📋 输出示例

搜索结果按文件类型分不同表格展示，表格自动按 CJK 显示并对齐宽度列表，文件大小以 TB/GB/MB/KB/B 为单位换算，更易读：

```

🎊 共找到 4 个结果，按类型列表如下 🎊

🎵 音乐（共 2 个）
文件名            扩展名     大小     修改日期            路径
----------------------------------------------------------------------------------
陈绮贞 - 鱼       .flac      8.9 MB   2025-01-06 23:48   D:\Music\
陈绮贞 - 鱼_钢琴  .mid       14.2 KB  2026-07-21 23:02   C:\Users\...\


📎 其他文件（共 1 个）
文件名            扩展名     大小     修改日期            路径
----------------------------------------------------------------------------------
陈绮贞 - 鱼       .lnk       1.2 KB   2026-07-25 12:14   C:\Users\...\Recent\


📁 文件夹（共 1 个）
文件名                       大小       修改日期           路径
----------------------------------------------------------------------------------
陈绮贞 - 鱼                  235.1 MB   2026-07-22 12:04  C:\Users\separated_full\

```

> 不同文件类型的表格排序：音乐 → 视频 → 图片 → 文档 → 压缩包 → 其他文件 → 文件夹

---

## 🎯 适用场景

### ✅ 现适用于 -- 本地文件名、文件属性

- 📂 **文件名/路径检索** — 按文件名、扩展名、大小、路径定位\筛选本地文件
- 🎵 **媒体文件定位** — 查找音乐、视频、图片等本地资源

### ❌ 暂不适用 -- 网络搜索、文件内容、语义搜索、非 windows 平台

- 📝 **内容搜索** — 暂不支持搜索\定位文件内部文本/代码（Everything1.5测试版已支持，后续该技能会补齐这个功能）
- 🎶 **语义搜索** — 如 电脑里只有名为陈绮贞的歌曲，但搜索CheerChen的歌曲（未来会支持）
- 🍎 **非 Windows 平台** — 依赖于Everything，目前只支持 Windows 10/11 与 WSL2（Linux & macOS正在开发中...）

---

## 🔍 探测机制

`find_es_exe()` 采用 **多层探测**定位 `es.exe`，依次尝试直至命中。该机制保证在多种安装方式（默认安装、自定义path路径、环境变量、PATH 注册等）下均能自动配置好技能包，减少用户手动配置。

<p align="center">
  <img src="docs/discovery-priority.svg" alt="路径发现优先级" width="880"/>
</p>

探测顺序如下（命中即返回）：

| 优先级 | 来源 |
| :---: | --- |
| 1 | 运行中的 `Everything.exe` 进程所在目录 |
| 2 | `path.env` 中自动写入的 `ES_PATH` |
| 3 | 环境变量 `EVERYTHING_PATH` 下的 `es.exe` |
| 4 | 常用安装路径（`C:\Program Files\Everything` 等） |
| 5 | 环境变量 `ES_PATH` |
| 6 | 系统 `PATH` 中的 `es.exe` |

> 💡 **说明**：Level 1–3 为常用命中路径；4–6 为补充兜底。配置成功后路径写入 `path.env`，后续调用直接命中前几级，减少重复探测，加速本地搜索。

---

## 📁 项目结构

```text
everything-search-skill/
│
├─ ✅ SKILL.md                       # Skill 描述文件（Agent 识别入口）
├─ ✅ scripts/
│   ├─ ✅ install.py                 # 安装发现脚本（路径发现 · 后台启动 · 配置路径）
│   └─ ✅ search_core.py             # 核心搜索脚本（关键词提取 · es.exe 调用 · 结果格式化）
│
├─ 📄 README.md                      # 中文发布页
├─ 📄 LICENSE                        # MIT 许可证
├─ 📄 docs/                          # 文档资源（架构图 · 流程图 · 配图）
│   ├─ architecture.svg              #   系统架构图（中文）
│   ├─ search-flow-xiaohei.png       #   搜索全流程 Ian 小黑配图（正文主图）
│   └─ discovery-priority.svg        #   路径发现优先级图（中文）
│
├─ 📄 .gitignore                     # 克隆忽略规则
│
└─ 📦 path.env                       # 路径配置（首次运行 install.py 时自动生成）
```

> ✅ 为 运行核心文件 -- 推荐只安装这些就够了，保证技能包的精简
> 📄 为 文档资源 -- 仅供 GitHub 发布页展示使用

<p align="center">
  <img src="docs/architecture.svg" alt="系统架构图" width="880"/>
</p>

---

## ⚠️ 注意事项

1. **Everything 需运行** — `es.exe` 依赖 Everything 的 IPC 接口，搜索前 Everything 需处于运行中。本 Skill 会在检测到未运行时自动后台启动Everything（但仍建议您将Everything设为开机自启动）

2. **`es.exe` 位置！！！** — 必须与 `Everything.exe` 同目录，即Everything文件夹中，否则 Level 0 进程检测失效。若放置在其他目录，推荐您将它移入。（注：voidtools 默认不会并且我们也不推荐将es.exe加入系统PATH）

3. **权限要求** — 访问部分目录（如系统目录`C:\Program Files`）下的文件可能需要读取权限；推荐：安装Everything时配置管理员权限可以获得更完整的索引覆盖。（以管理员身份运行 Everything 更好）

4. **WSL2 用户** — 需确保 Everything 安装在 Windows 宿主侧。（WSL2内会通过 `cmd.exe` 桥接调用 `tasklist` 与 Everything 可执行文件）

5. **搜索语法** — 支持全套的 Everything 的搜索语法（如 `*.pdf`、`report`、`ext:docx;pdf`、`size:>100mb`、`path:C:\Users`、`dm:2026` 等），更多请参考[Everything 所有搜索语法](https://www.voidtools.com/support/everything/searching/)
---

## ❓ 常见问题

<details>
<summary><b>Q1：运行搜索时报错"es.exe 未找到"怎么办？</b></summary>
请按以下步骤排查：
1. 确认已下载解压得到并放 `es.exe` 到 Everything 安装目录下（与 `Everything.exe` 同级）。
2. 重新让智能体进行搜索，或手动运行 `python scripts/install.py`即可

</details>

<details>
<summary><b>Q2：搜索结果还是出现中文乱码？</b></summary>
本技能内置了多种中文编码检测机制（utf-8 / gbk / cp1252 / shift-jis / utf-16-le）。若仍出现乱码，通常是 `es.exe` 版本过旧、异常或系统 locale 异常，建议升级至对应版本的 es.exe

</details>

<details>
<summary><b>Q3：搜索返回"Everything 未运行"但已启动？</b></summary>
可能是进程检测窗口（最多等待 5 秒）内 Everything 尚未完成初始化。请稍等片刻后重试，或将 Everything 设为开机自启以避免此问题。

</details>

<details>
<summary><b>Q4：如何重置配置？</b></summary>
删除技能包目录下的 `path.env` 文件即可。

</details>

<details>
<summary><b>Q5：装了多个 Everything（如 1.4 和 1.5 并存），怎么指定用哪一个？</b></summary>
用 `--install` 指定你想用的那份，它的优先级高于"运行中的 Everything 进程"检测，不会被自动探测顶掉：

```bash
python scripts/install.py "D:\Everything1.4" --install
```

只想换 `es.exe`、保留原来的 `Everything.exe` 配置，则把 `es.exe` 的完整路径传进去即可（反之同理）：

```bash
python scripts/install.py "D:\Everything1.4\es.exe" --install
```

</details>

<details>
<summary><b>Q6：能否在 Linux/macOS 上使用？</b></summary>
暂不支持，还在开发中，请稍等哦~

</details>

---

## 📚 参考资料

- [Everything 下载](https://www.voidtools.com/zh-cn/downloads/)
- [Everything es.exe 下载](https://www.voidtools.com/zh-cn/downloads/#cli)

- [Everything 所有搜索语法](https://www.voidtools.com/support/everything/searching/)
- [Everything 更多帮助信息](https://www.voidtools.com/zh-cn/support/everything/)

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源，可自由使用、修改与分发。

Everything 和 `es.exe` 为 [voidtools](https://www.voidtools.com/) 的独立产品，其版权归原作者所有，使用时请遵循其相应许可协议。
OneToken已向作者授权使用 `es.exe` 作为本 Skill 的核心组件，并在此基础上进行功能封装与优化，再次感谢原作者的支持！！！！

---

<div align="center">

</div>
