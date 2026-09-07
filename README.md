# biliaudio

B站视频/音频提取工具，支持交互式 CLI 界面，可选择提取音频或视频，支持多种主流格式输出。

## 安装

```bash
npm install -g biliaudio
```

安装完成后，在任意目录输入 `biliaudio` 即可启动。

### 前置要求

- Node.js >= 16
- Python >= 3.10
- ffmpeg（视频合并和音频转码必需）

## 使用

```bash
biliaudio
```

### 配置文件

首次运行后会在 `~/.config/biliaudio/config.toml` 生成配置文件：

```toml
[cookie]
# Cookie 文件路径（Netscape 格式）
# 留空则不使用 Cookie，启动时询问
path = ""

[download]
# 默认下载目录（留空则使用当前目录）
output_dir = ""

# 默认音频格式: mp3, aac, flac, m4a, opus, wav
audio_format = "mp3"

# 默认视频格式: mp4, mkv, webm
video_format = "mp4"
```

编辑配置文件可预设 Cookie 路径、下载目录和默认格式。

### Cookie 配置

下载高清/会员内容需要 Cookie。将导出的 Netscape 格式 Cookie 文件路径填入配置文件的 `cookie.path` 字段。

## 功能特性

- 交互式 CLI 界面，操作简单直观
- 支持音频提取：MP3、AAC、FLAC、M4A、Opus、WAV
- 支持视频下载：MP4、MKV、WebM
- 实时下载进度显示
- Cookie 支持，可下载高清/会员内容
- 支持 BV号、av号、b23.tv 短链接

## 依赖

- `yt-dlp` - 下载引擎
- `rich` - 终端美化输出
- `questionary` - 交互式选择
- `tomli` - TOML 配置解析（Python < 3.11）

## 许可证

MIT License
