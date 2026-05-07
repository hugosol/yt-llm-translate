
下载并自动生成YouTube 视频及双语字幕的skill（适用于[opencode](https://github.com/anomalyco/opencode)）

- [Why this exists](#why-this-exists)
- [Installation](#installation)
- [Usage](#usage)
- [Design](#design)
  - [Main Progress](#main-progress)
  - [Scripts](#scripts)
  - [Skills](#skills)
  - [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [License](#license)

# Why this exists

- 以 Skill 形式分发，无需安装 — 复制文件夹到 opencode skills 目录即可使用。opencode 的 Web 模式支持局域网内任意设备远程触发，比传统客户端更灵活。

- 输出本地文件（.mp4 / .srt），字幕文本便于后续交给 AI 进行知识整理，本地视频也可配合 [my-streaming](https://github.com/hugosol/my-streaming) 于局域网内使用便携设备串流播放。

- 处理效率：以 DeepSeek V4 Flash、4 线程处理 15 分钟视频，耗时约 2–3 分钟。LLM 自动添加标点、重新断句，提升可读性。多线程处理大文件，LLM 调度任务灵活应对异常，确保每个子任务稳定完成。

原生字幕：
![image](https://github.com/user-attachments/assets/1829c81f-a235-4906-b015-87b9c836d718)
优化后：
![image](https://github.com/user-attachments/assets/6da38683-ef60-41ee-889d-6588bc6e7710)

---
## Installation
开始前请确保已安装以下项目：

| dependency                                               | 说明                                | 安装指引                                                                           |
| -------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------ |
| Python                                                   | Python 3.14.2以上版本                 | [python download](https://www.python.org/downloads/)                                              |
| Firefox                                                  | 用于获取油管用户cookies                   | [firefox](https://www.firefox.com/zh-CN/)                                                 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp)               | 老牌视频站学习工具                         | [yt-dlp#installation](https://github.com/yt-dlp/yt-dlp#installation)                                  |
| [FFmpeg-Builds](https://github.com/yt-dlp/FFmpeg-Builds) | 一个适用于yt-dlp的稳定FFmpeg发布版本，用于烧录输出视频 | [FFmpeg-Builds#downloads](https://github.com/yt-dlp/FFmpeg-Builds#downloads)                              |
| [opencode](https://github.com/anomalyco/opencode)        | 最新最潮开源Agentic CLI                 | [opencode#installation](https://github.com/anomalyco/opencode/blob/dev/README.zh.md#%E5%AE%89%E8%A3%85) |
| 一个可以访问油管的节点                                              | 略                                 | 略                                                                              |

引入skill：
1. 如果你是第一次使用yt-dlp和FFmpeg，请将他们添加至system path（环境变量）
2. 安装skill: git clone 本项目文件至任意目录下，进入yt-llm-translate/.opencode，启动opencode TUI，即可加载三个skill
（亦可选择把yt-llm-translate/.opencode/skills目录下三个文件夹直接放置于全局skills目录下）
3. 修改配置：打开配置文件./.opencode/skills/yt-llm-translate/scripts/config.json
   ，修改以下配置，示例：
  ```json
  {
     "debug": false,
     "model": "deepseek/deepseek-v4-flash",
     "yt-download-proxy": "http://127.0.0.1:10808",
     "opencode_path": "D:\\nvm4w\\nodejs\\opencode.ps1",
     "translation": {
       "chunk_size": "auto",
       "min_size": 30,
       "max_size": 100,
       "thread_num": 4
      },
     "punctuation_check": {
       "expected_per_lines": 0.333,
       "threshold_factor": 0.4
     }
  }
  ```
  - model: 设置你在文本处理时想使用的模型，填入内容参见[opencode-docs#model](https://opencode.ai/docs/zh-cn/commands/#model)
  - yt-download-proxy: 运行yt-dlp时使用的代理地址及端口，用于下载youtube视频及字幕
  - opencode-path: 填写你本地的opencode路径（如果用npm安装可用npm list -g opencode-ai 查看）

# Usage
1. （第一次使用时）firefox打开[youtube](https://www.youtube.com/)，登录你的账号以获取cookies
2. 从opencode进行对话：
```
请帮我下载并翻译视频：https://www.youtube.com/watch?v=ONIBOhQiaRw
```
等待任务完成...
当前目录下将出现两个文件：
```
vedio_name.mp4
vedio_name.en.srt
```
Enjoy it!

---

# Design
## Main Progress

```
YouTube URL
    │
    ▼
[下载]  yt-dlp 下载视频 +油管语音识别英文字幕 (.en.srt)
    │
    ▼
[标点]  srt-punctuator 通过 LLM 为英文添加标点符号
    │
    ▼
[分句]  resegment.py 按标点重切时间轴，拆长句、合并短句
    │
    ▼
[翻译]  batch_translate.py 分块并发调用 chunk-translator，逐块翻译
    │
    ▼
[合并]  combine-subtitles.ps1 将中英文合并为双语 SRT
    │
    ▼
最终结果：
xxx.en.srt + xxx.mp4
```

## Scripts
- `download.ps1` — 下载 YouTube 视频及自动英文字幕，并修复 SRT 字幕时间轴重叠问题。

  | 参数               | 类型     | 必填 | 默认值     | 说明                                                       |
  | ----------------- | -------- | ---- | --------- | ---------------------------------------------------------- |
  | `-Url`            | string   | 是   | —         | YouTube 视频链接（第1个位置参数）                               |
  | `-Proxy`          | string   | 否   | 自动读取   | yt-dlp 下载代理地址（如 `http://127.0.0.1:10808`），未指定时自动从 `config.json` 读取 |
  | `-NoProxy`        | switch   | 否   | —         | 强制禁用代理，即使配置文件中有设置                                |
  | `-CookiesBrowser` | string   | 否   | `firefox` | 读取 cookies 的浏览器（用于登录验证）                             |
  | `-OutputDir`      | string   | 否   | `.`       | 输出目录                                                     |

  调用示例：
  ```powershell
  .\download.ps1 "https://www.youtube.com/watch?v=ONIBOhQiaRw"
  .\download.ps1 -Url "..." -Proxy "http://127.0.0.1:10808" -OutputDir "./output"
  ```

  下载完成后自动修复 SRT 字幕中的时间轴重叠问题，将每条字幕的结束时间调整为下一条的开始时间，同时去除文件名中的 `-orig` 后缀。

- `resegment.py` — 按标点符号重新切分 SRT 字幕时间轴，拆长句、合并短句，生成更均匀的断句。

  | 参数          | 类型     | 必填 | 默认值                     | 说明                                |
  | ------------ | -------- | ---- | ------------------------- | ----------------------------------- |
  | `input.srt`  | string   | 是   | —                         | 输入 SRT 文件（第1个位置参数）            |
  | `output.srt` | string   | 否   | `{input}_resegmented.srt` | 输出文件路径（第2个位置参数）              |
  | `--max-len`  | int      | 否   | `62`                      | 单行最大字符数，超出则按空格拆分             |

  调用示例：
  ```bash
  python resegment.py sample.srt
  python resegment.py sample.srt output.srt --max-len 50
  ```

  处理流程：合并字幕文本 → 按标点（`,.?!;`）拆分为句子级分段 → 超长行按空格二分 → 合并过短的相邻句子 → 插值分配时间戳 → 写入新 SRT，原文件重命名为 `.srt-bak` 备份。

- `batch_translate.py` — 将 SRT/TXT 英文文本分块并发翻译为中文，输出中英对照文件或双语 SRT。
  
  `chunk_size`、`thread_num`、`opencode_path` 等参数从 `config.json` 读取，无需命令行传入。

  | 参数                    | 类型     | 必填 | 默认值                                | 说明                                         |
  | ---------------------- | -------- | ---- | ------------------------------------ | ------------------------------------------- |
  | `input_file`           | string   | 是   | —                                    | 输入 `.srt` 或英文 `.txt` 文件（第1个位置参数）       |
  | `--no-sentence-boundary` | flag   | 否   | —                                    | 禁用句子边界检测，严格按 `chunk_size` 硬切分              |
  | `--max-lookahead`      | int      | 否   | `30`                                 | 句子边界检测时最大前瞻行数                            |
  | `--output-dir`         | string   | 否   | `{input}_workspace/chunks`           | 分块文件输出目录                                  |
  | `--timeout`            | int      | 否   | `600`                                | 每个翻译块的超时时间（秒）                            |
  | `--log-filter`         | choice   | 否   | `minimal`                            | 日志过滤级别：`none` / `quiet` / `minimal`        |
  | `--no-extract`         | flag     | 否   | —                                    | 跳过 SRT 文本提取，将输入视为纯文本                      |
  | `--no-combine`         | flag     | 否   | —                                    | 跳过最终的双语 SRT 合并步骤                          |

  调用示例：
  ```bash
  python batch_translate.py video.en.srt
  python batch_translate.py english.txt --no-extract
  ```

   处理流程：SRT → 提取纯文本 → 按句子边界分块 → 多线程调用 `chunk-translator` 逐块翻译 → 聚合中文结果 → 合并双语 SRT（覆盖原文件）。

- `run_opencode.py` — 调用 opencode 执行指定 prompt，等待任务完成后验证目标文件是否生成。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| ------------------ | -------- | ---- | ------------------------- | ------------------------------------------------ |
| `--prompt`         | string   | 是   | —                         | 发送给 opencode 的提示语 |
| `--expected-file` | string   | 是   | —                         | 任务完成后检查的目标文件路径 |
| `--workdir`        | string   | 否   | `.`                       | opencode 工作目录 |
| `--log-file`       | string   | 否   | `opencode_run.log`        | 日志输出文件路径 |
| `--timeout`        | int      | 否   | `600`                     | 超时时间（秒），`0` 表示无限制 |
| `--log-filter`     | choice   | 否   | `minimal`                 | 日志过滤级别：`none` / `quiet` / `minimal` |

`opencode-path` 与 `model` 直接从 `config.json` 读取，不再作为命令行参数传入。

  调用示例：
  ```bash
  python run_opencode.py --prompt "请翻译以下文本..." --expected-file "./output.txt"
  python run_opencode.py --prompt "..." --expected-file "result.srt" --timeout 1200 --log-filter quiet
  ```

  启动 opencode 子进程执行指定任务，实时输出日志，超时自动终止；完成后检查 `--expected-file` 是否存在并报告结果。


## Skills
- `yt-llm-translate` — 主控 Skill，编排完整流水线：下载 YouTube 视频 → 标点修复 → 重切时间轴 → 翻译 → 合并双语字幕。

  - **输入**：YouTube 视频链接（通过对话自然语言触发）
  - **输出**：`视频名.mp4` + `视频名.en.srt`（中英双语字幕）
  - **流程**：调用 `entry.py <youtube_url>` 串联 `download.ps1` → `srt-punctuator` → `resegment.py` → `batch_translate.py` → `combine-subtitles.ps1`

- `srt-punctuator` — 为 AI 生成的英文 SRT 字幕添加规范标点符号（句号、逗号、问号等）。

  - **输入**：无标点的英文字幕 `.srt` 文件
  - **输出**：原地替换为带标点的 `.srt`（原文件被覆盖）
  - **流程**：
    1. `srt_marker.py prepare` — 用 `<<N>>` 标记定位每条字幕，合并为单行待标点文本
    2. LLM 标点 — 在标记之间添加英文标点，不修改标记本身
    3. `srt_marker.py finalize` — 拆分回原时间轴，验证后替换原文件

- `chunk-translator` — 将英文纯文本字幕块翻译为流畅中文，采用「整体翻译 → 智能拆分」两步法。

  - **输入**：英文纯文本 `.txt` 文件（每行一句，无时间码）
  - **输出**：`{原文件名}_chinese.txt`（行数严格等于输入，逐行语义对应）
  - **核心原则**：
    - 先合并全文整体翻译，保证上下文连贯、意译自然
    - 再按原文行数拆分，逐行语义对齐、行数严格相等

## Configuration
```json
{
  "debug": false,
  "model": "deepseek/deepseek-v4-flash",
  "yt-download-proxy": "http://127.0.0.1:10808",
  "opencode_path": "D:\\nvm4w\\nodejs\\opencode.ps1",
  "translation": {
    "chunk_size": "auto",
    "min_size": 30,
    "max_size": 100,
    "thread_num": 4
  },
  "punctuation_check": {
    "expected_per_lines": 0.333,
    "threshold_factor": 0.4
  }
}
```

| 字段                       | 说明                                                     |
| ------------------------ | ------------------------------------------------------ |
| `debug`                  | 开启后保留日志及中间文件，方便排查                                      |
| `model`                  | LLM 模型，格式`provider/model`                              |
| `yt-download-proxy`      | yt-dlp 下载代理地址，不需要可设为空字符串`""`                           |
| `opencode_path`          | opencode 可执行文件路径                                       |
| `translation.chunk_size` | 每个翻译块的英文行数，该参数越大上下文一致性越好，但请求时间将相应变长，`"auto"` 根据线程数自动计算 |
| `translation.min_size`   | `chunk_size=auto` 时的最小块大小                              |
| `translation.max_size`   | `chunk_size=auto` 时的最大块大小                              |
| `translation.thread_num` | 并发翻译线程数                                                |
| `punctuation_check`      | 决定是否需要为原字幕添加标点的相关参数，一般无需修改                             |

# Troubleshooting 
config.json中将debug设为true，可查看每一步骤的输出结果以及日志

# License

MIT License — 详见 [LICENSE.txt](./LICENSE.txt)
