# Bilibili Extractor

B站视频/音频提取工具，支持交互式 CLI 界面，可选择提取音频或视频，支持多种主流格式输出。

## 功能特性

- 交互式 CLI 界面，操作简单直观
- 支持音频提取：MP3、AAC、FLAC、M4A、Opus、WAV
- 支持视频下载：MP4、MKV、WebM
- 实时下载进度显示（速度、大小）
- Cookie 支持，可下载高清/会员内容
- 自动检测浏览器 Cookie（Firefox）
- 支持 BV号、av号、b23.tv 短链接

## 环境要求

- Python 3.10+
- ffmpeg（视频合并和音频转码必需）

## 安装

```bash
# 克隆仓库
git clone https://github.com/BakaXXXXXL/budio.git
cd budio

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 直接运行

```bash
python3 bilibili_extractor.py
```

### 配置全局命令

在 `~/.bashrc` 中添加：

```bash
alias biliaudio="python3 /path/to/bilibili_extractor.py"
```

然后执行 `source ~/.bashrc`，即可在任意目录使用 `biliaudio` 命令启动。

## Cookie 配置

下载高清或会员内容需要 Cookie。

### 方法一：自动使用（推荐）

将 `cookie.txt` 文件放在脚本同目录下，脚本会自动加载。

### 方法二：手动导入

1. 在 Edge 商店搜索 `cookies.txt` 或 `cookie editor` 扩展
2. 安装后访问 bilibili.com 并登录
3. 使用扩展导出 Netscape 格式的 Cookie 文件
4. 运行脚本时选择「从文件导入Cookie」

### Firefox 用户

Firefox 的 Cookie 可自动提取，无需额外配置。

## 依赖

```
yt-dlp>=2024.1.0
rich>=13.0.0
questionary>=2.0.0
```

## 许可证

MIT License
