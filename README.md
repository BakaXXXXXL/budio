# budio

B站视频/音频提取工具，支持交互式 CLI 界面，可选择提取音频或视频，支持多种主流格式输出。

## 安装

### 前置要求

- Node.js >= 16
- Python >= 3.10
- ffmpeg（视频合并和音频转码必需）

**Ubuntu/Debian:**
```bash
sudo apt install python3 ffmpeg
```

**macOS:**
```bash
brew install python3 ffmpeg
```

### 安装 budio

**方式一：从 GitHub 安装**
```bash
npm config set fetch-git true
npm config set fetch-remote true
npm install -g github:BakaXXXXXL/budio
```
> 注意：npm v12+ 默认禁止外部源，需先执行上面两行配置

**方式二：克隆仓库后本地安装**
```bash
git clone https://github.com/BakaXXXXXL/budio.git
cd budio
npm install -g .
```

安装完成后，在任意目录输入 `budio` 即可启动。

## 卸载

```bash
npm uninstall -g budio
```

删除配置文件（可选）：
```bash
rm -rf ~/.config/budio
```

## 使用

```bash
cd ~/Music
budio
```

文件将下载到当前终端所在目录。

### 首次运行

首次运行时会引导你设置 Cookie（可跳过）：
- 粘贴 Netscape 格式的 Cookie 内容，自动保存
- 直接回车跳过，后续可在配置文件中设置

### 配置文件

配置文件位于 `~/.config/budio/config.toml`：

```toml
[cookie]
# Cookie 文件路径（Netscape 格式）
# 留空则启动时询问
path = ""

[download]
# 默认下载目录（留空则使用当前目录）
output_dir = ""

# 默认音频格式: mp3, aac, flac, m4a, opus, wav
audio_format = "mp3"

# 默认视频格式: mp4, mkv, webm
video_format = "mp4"
```

### Cookie 获取

下载高清/会员内容需要 Cookie。获取步骤：
1. 在浏览器安装 Cookie Editor 扩展
2. 访问 bilibili.com 并登录
3. 点击扩展导出 Netscape 格式 Cookie
4. 将内容粘贴到首次运行的提示中，或保存为文件后配置 `cookie.path`

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
