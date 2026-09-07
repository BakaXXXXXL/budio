#!/usr/bin/env python3
"""B站视频/音频提取工具 - 交互式CLI界面，支持多种格式输出。"""

import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import questionary
import yt_dlp
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()

BANNER = Text.from_markup(
    "[bold cyan]╔═══════════════════════════════════╗\n"
    "║     B站视频/音频提取工具 v1.0    ║\n"
    "╚═══════════════════════════════════╝[/bold cyan]"
)

AUDIO_FORMATS = {
    "MP3": "mp3",
    "AAC": "aac",
    "FLAC": "flac",
    "M4A": "m4a",
    "Opus": "opus",
    "WAV": "wav",
}

VIDEO_FORMATS = {
    "MP4": "mp4",
    "MKV": "mkv",
    "WebM": "webm",
}

AUDIO_QUALITIES = {
    "最佳 (VBR 0)": "0",
    "高质量 (VBR 2)": "2",
    "中等 (VBR 5)": "5",
    "低质量 (VBR 9)": "9",
    "128K": "128K",
    "192K": "192K",
    "256K": "256K",
    "320K": "320K",
}

BILIBILI_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:bilibili\.com/(?:video/|festival/[^/?#]+\?(?:[^#]*&)?bvid=)[aAbB][vV][^/?#&]+|b23\.tv/\S+)"
)


def load_config() -> dict:
    """加载 TOML 配置文件。"""
    default_config = {
        "cookie": {"path": ""},
        "download": {"output_dir": "", "audio_format": "mp3", "video_format": "mp4"},
    }

    # 配置文件查找顺序
    home = Path.home()
    config_paths = [
        home / ".config" / "budio" / "config.toml",
        Path(__file__).parent.parent / "config" / "biliaudio.toml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)
                # 合并默认值
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                    else:
                        for k, v in default_config[key].items():
                            if k not in config[key]:
                                config[key][k] = v
                return config
            except Exception:
                pass

    return default_config


def init_user_config():
    """首次运行时，将默认配置复制到用户目录，并引导用户输入Cookie。"""
    user_config_dir = Path.home() / ".config" / "budio"
    user_config_file = user_config_dir / "config.toml"

    if user_config_file.exists():
        return False

    # 查找包内默认配置
    default_config = Path(__file__).parent.parent / "config" / "biliaudio.toml"
    if default_config.exists():
        user_config_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(default_config, user_config_file)

    return True

COOKIE_HELP_TEXT = """
[bold]Cookie 获取方法 (用于下载高清/会员内容):[/bold]

[yellow]方法1: 使用浏览器扩展 (推荐)[/yellow]
  1. 在 Edge 商店搜索 "cookies.txt" 或 "cookie editor"
  2. 安装一个扩展 (如 "Cookie Editor" 或 "Get cookies.txt")
  3. 访问 bilibili.com 并登录
  4. 使用扩展导出 cookies (Netscape/HTTP Cookie File 格式)
  5. 保存为 cookies.txt 文件
  6. 重新运行本工具，选择「从文件导入Cookie」

[yellow]方法2: 不使用Cookie (仅下载免费内容)[/yellow]
  大部分B站视频无需登录即可下载，只有高清(1080p+)和会员内容需要Cookie。
"""


def validate_url(url: str) -> bool:
    return bool(BILIBILI_URL_PATTERN.match(url.strip()))


def format_duration(seconds: int | float | None) -> str:
    if seconds is None:
        return "未知"
    s = int(seconds)
    h, remainder = divmod(s, 3600)
    m, sec = divmod(remainder, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def format_size(nbytes: int | float | None) -> str:
    if nbytes is None:
        return "未知"
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def fetch_video_info(url: str, cookies_from_browser: str | None = None, cookie_file: str | None = None) -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
    elif cookie_file:
        ydl_opts["cookiefile"] = cookie_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def display_video_info(info: dict):
    table = Table(show_header=False, border_style="cyan", padding=(0, 2))
    table.add_column("字段", style="bold")
    table.add_column("值")

    title = info.get("title", "未知")
    uploader = info.get("uploader", "未知")
    duration = format_duration(info.get("duration"))
    view_count = info.get("view_count")
    view_str = f"{view_count:,}" if view_count else "未知"
    upload_date = info.get("upload_date", "")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    else:
        upload_date = "未知"

    table.add_row("标题", title)
    table.add_row("UP主", uploader)
    table.add_row("时长", duration)
    table.add_row("播放量", view_str)
    table.add_row("上传日期", upload_date)

    console.print()
    console.print(Panel(table, title="[bold]视频信息[/bold]", border_style="cyan"))


def create_progress_hook(progress: Progress, task_id) -> str:
    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed")
            if total:
                progress.update(task_id, total=total, completed=downloaded)
                if speed:
                    progress.update(
                        task_id,
                        speed=speed,
                    )
        elif d["status"] == "finished":
            progress.update(task_id, description="[green]处理中...[/green]")

    return hook


def download_audio(
    url: str,
    codec: str,
    quality: str,
    output_dir: str,
    cookies_from_browser: str | None = None,
    cookie_file: str | None = None,
):
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": codec,
                "preferredquality": quality,
            }
        ],
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
    }
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
    elif cookie_file:
        ydl_opts["cookiefile"] = cookie_file

    with Progress(
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(f"下载音频 ({codec.upper()})", total=None)
        hook = create_progress_hook(progress, task_id)

        ydl_opts["progress_hooks"] = [hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])


def download_video(
    url: str,
    container: str,
    output_dir: str,
    cookies_from_browser: str | None = None,
    cookie_file: str | None = None,
):
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    format_str = f"bestvideo[ext={container}]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    if container == "mkv":
        format_str = "bestvideo+bestaudio/best"

    ydl_opts = {
        "format": format_str,
        "merge_output_format": container,
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
    }
    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
    elif cookie_file:
        ydl_opts["cookiefile"] = cookie_file

    with Progress(
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(f"下载视频 ({container.upper()})", total=None)
        hook = create_progress_hook(progress, task_id)

        ydl_opts["progress_hooks"] = [hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])


def find_downloaded_file(output_dir: str) -> str | None:
    files = sorted(Path(output_dir).glob("*"), key=os.path.getmtime, reverse=True)
    for f in files:
        if f.is_file() and not f.name.startswith("."):
            return str(f)
    return None


def detect_browsers() -> list[dict]:
    """检测系统中已安装的浏览器，包括Windows侧（WSL2）。"""
    home = Path.home()
    browsers = []

    # Linux 本地浏览器
    linux_browsers = {
        "chrome": home / ".config" / "google-chrome",
        "chromium": home / ".config" / "chromium",
        "edge": home / ".config" / "microsoft-edge",
        "brave": home / ".config" / "BraveSoftware" / "Brave-Browser",
        "firefox": home / ".mozilla" / "firefox",
    }
    for name, path in linux_browsers.items():
        if path.exists():
            browsers.append({"name": name, "platform": "linux", "path": path})

    # Windows 浏览器 (WSL2)
    mnt_c = Path("/mnt/c")
    if mnt_c.exists():
        users_dir = mnt_c / "Users"
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir() or user_dir.name in ("All Users", "Default", "Default User", "Public"):
                continue

            # Windows Firefox
            ff_profiles = user_dir / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
            if ff_profiles.exists():
                for profile in ff_profiles.iterdir():
                    cookies_file = profile / "cookies.sqlite"
                    if cookies_file.exists():
                        browsers.append({
                            "name": f"firefox (Windows - {profile.name})",
                            "platform": "windows",
                            "browser": "firefox",
                            "profile_path": str(profile),
                        })

            # Windows Edge (Chromium-based, cookies in Network/Cookies)
            edge_profiles = user_dir / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data"
            if edge_profiles.exists():
                for profile_dir in edge_profiles.iterdir():
                    if profile_dir.is_dir():
                        # Check Network/Cookies (Chromium standard) or Cookies
                        cookies_path = profile_dir / "Network" / "Cookies"
                        if not cookies_path.exists():
                            cookies_path = profile_dir / "Cookies"
                        if cookies_path.exists() and cookies_path.stat().st_size > 0:
                            browsers.append({
                                "name": f"edge (Windows - {profile_dir.name})",
                                "platform": "windows",
                                "browser": "edge",
                                "profile_path": str(profile_dir),
                                "cookies_path": str(cookies_path),
                            })

            # Windows Chrome (Chromium-based, cookies in Network/Cookies)
            chrome_profiles = user_dir / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
            if chrome_profiles.exists():
                for profile_dir in chrome_profiles.iterdir():
                    if profile_dir.is_dir():
                        cookies_path = profile_dir / "Network" / "Cookies"
                        if not cookies_path.exists():
                            cookies_path = profile_dir / "Cookies"
                        if cookies_path.exists() and cookies_path.stat().st_size > 0:
                            browsers.append({
                                "name": f"chrome (Windows - {profile_dir.name})",
                                "platform": "windows",
                                "browser": "chrome",
                                "profile_path": str(profile_dir),
                                "cookies_path": str(cookies_path),
                            })

    return browsers


def firefox_cookies_to_netscape(profile_path: str, output_path: str) -> bool:
    """将 Firefox cookies.sqlite 转换为 Netscape 格式。"""
    cookies_db = Path(profile_path) / "cookies.sqlite"
    if not cookies_db.exists():
        return False

    # 复制数据库避免锁定问题
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = tmp.name
    shutil.copy2(cookies_db, tmp_path)

    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()

        # 获取 Bilibili 相关 cookies
        cursor.execute("""
            SELECT host, name, value, path, expiry, isSecure, isHttpOnly
            FROM moz_cookies
            WHERE host LIKE '%bilibili%' OR host LIKE '%bili%'
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            console.print("[yellow]警告:[/yellow] 未找到B站相关Cookie")
            console.print("  请先在Windows浏览器中登录B站，然后重试。")
            return False

        # 写入 Netscape 格式
        with open(output_path, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This file was generated by bilibili_extractor\n\n")
            for host, name, value, path, expiry, secure, http_only in rows:
                secure_str = "TRUE" if secure else "FALSE"
                http_only_str = "TRUE" if http_only else "FALSE"
                domain_flag = "TRUE" if host.startswith(".") else "FALSE"
                f.write(f"{host}\t{domain_flag}\t{path}\t{secure_str}\t{expiry}\t{name}\t{value}\n")

        console.print(f"[green]已提取 {len(rows)} 条Cookie[/green]")
        return True

    finally:
        os.unlink(tmp_path)


def chromium_cookies_to_netscape(cookies_path: str, output_path: str) -> bool:
    """将 Chromium (Edge/Chrome) Cookies 转换为 Netscape 格式。"""
    cookies_db = Path(cookies_path)
    if not cookies_db.exists():
        console.print(f"[red]Cookie文件不存在:[/red] {cookies_path}")
        return False

    # 复制数据库避免锁定问题
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copy2(cookies_db, tmp_path)
    except PermissionError:
        console.print("[red]无法读取Cookie文件:[/red] 浏览器正在运行并锁定文件")
        console.print("[yellow]解决方法:[/yellow]")
        console.print("  1. 关闭所有浏览器窗口")
        console.print("  2. 重新运行本工具")
        console.print("  或者：手动导出Netscape格式cookie文件，使用 --cookies 参数")
        return False

    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()

        # Chromium cookies 表结构：host_key, name, value, path, expires_utc, is_secure, is_httponly
        # 注意：Chromium 的 value 可能是加密的，encrypted_value 不能直接读取
        cursor.execute("""
            SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly
            FROM cookies
            WHERE host_key LIKE '%bilibili%' OR host_key LIKE '%bili%'
        """)
        rows = cursor.fetchall()
        conn.close()

        # 过滤掉空 value 的记录（可能是加密的）
        valid_rows = [(h, n, v, p, e, s, h2) for h, n, v, p, e, s, h2 in rows if v]

        if not valid_rows:
            console.print("[yellow]警告:[/yellow] 未找到B站相关Cookie")
            console.print("  请先在Windows浏览器中登录B站，然后重试。")
            return False

        # 写入 Netscape 格式
        with open(output_path, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This file was generated by bilibili_extractor\n\n")
            for host, name, value, path, expiry, secure, http_only in valid_rows:
                secure_str = "TRUE" if secure else "FALSE"
                domain_flag = "TRUE" if host.startswith(".") else "FALSE"
                # Chromium expires_utc 是微秒级时间戳，需要转换
                expiry_ts = int(expiry / 1000000) - 11644473600 if expiry > 0 else 0
                f.write(f"{host}\t{domain_flag}\t{path}\t{secure_str}\t{expiry_ts}\t{name}\t{value}\n")

        console.print(f"[green]已提取 {len(valid_rows)} 条Cookie[/green]")
        return True

    finally:
        os.unlink(tmp_path)


def main():
    console.print(BANNER)
    console.print()

    if not shutil.which("ffmpeg"):
        console.print(
            "[bold red]错误:[/bold red] 未找到 ffmpeg。请先安装 ffmpeg：\n"
            "  Ubuntu/Debian: [cyan]sudo apt install ffmpeg[/cyan]\n"
            "  macOS: [cyan]brew install ffmpeg[/cyan]\n"
            "  Arch: [cyan]sudo pacman -S ffmpeg[/cyan]"
        )
        sys.exit(1)

    # 初始化用户配置
    is_first_run = init_user_config()

    # 加载配置
    config = load_config()
    cookie_path = config.get("cookie", {}).get("path", "")
    if cookie_path:
        cookie_path = str(Path(cookie_path))
    default_output_dir = config.get("download", {}).get("output_dir", "")
    default_audio_fmt = config.get("download", {}).get("audio_format", "mp3")
    default_video_fmt = config.get("download", {}).get("video_format", "mp4")

    # 未配置Cookie时，提示用户粘贴
    if not cookie_path:
        if is_first_run:
            console.print("[bold]首次使用，欢迎使用 budio！[/bold]\n")
        console.print("[yellow]提示:[/yellow] 粘贴Cookie可下载高清/会员内容（Netscape格式）")
        console.print("  获取方法: 浏览器安装 Cookie Editor 扩展 → 访问 bilibili.com 登录 → 导出")
        console.print("  直接按回车跳过，仅下载免费内容\n")

        cookie_input = questionary.text("粘贴Cookie内容 (回车跳过):", default="").ask()
        if cookie_input and cookie_input.strip():
            user_config_dir = Path.home() / ".config" / "budio"
            cookie_file_path = user_config_dir / "cookies.txt"
            try:
                if "# Netscape" in cookie_input or "# Http Cookie File" in cookie_input:
                    user_config_dir.mkdir(parents=True, exist_ok=True)
                    with open(cookie_file_path, "w", encoding="utf-8") as f:
                        f.write(cookie_input)
                    config_file = user_config_dir / "config.toml"
                    if config_file.exists():
                        with open(config_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        toml_safe_path = str(cookie_file_path).replace("\\", "/")
                        content = content.replace('path = ""', f'path = "{toml_safe_path}"')
                        with open(config_file, "w", encoding="utf-8") as f:
                            f.write(content)
                    cookie_path = str(cookie_file_path)
                    console.print(f"[green]Cookie已保存[/green]\n")
                else:
                    console.print("[yellow]未识别到Netscape格式，跳过[/yellow]\n")
            except Exception as e:
                console.print(f"[red]保存Cookie失败: {e}[/red]\n")
        else:
            console.print("[cyan]已跳过[/cyan]\n")

    url = questionary.text("请输入B站视频链接:").ask()
    if not url:
        console.print("[red]已取消[/red]")
        return

    url = url.strip()
    if not validate_url(url):
        console.print("[red]无效的B站链接格式。支持的格式：bilibili.com/video/BV... 或 b23.tv/...[/red]")
        return

    available_browsers = detect_browsers()
    cookies_from_browser = None
    cookie_file = None

    # 检查配置文件中的 cookie 路径
    if cookie_path and os.path.exists(cookie_path):
        console.print(f"[green]自动使用Cookie文件: {cookie_path}[/green]")
        cookie_file = cookie_path
    else:
        # Cookie 选项
        cookie_choices = ["不需要Cookie (仅下载免费内容)"]
        if available_browsers:
            for b in available_browsers:
                cookie_choices.append(f"使用 {b['name']}")
        cookie_choices.append("从文件导入Cookie")
        cookie_choices.append("查看Cookie获取帮助")

        cookie_choice = questionary.select(
            "Cookie设置 (用于下载高清/会员内容):",
            choices=cookie_choices,
        ).ask()

        if cookie_choice is None:
            console.print("[red]已取消[/red]")
            return

        if cookie_choice.startswith("使用 "):
            # 选择浏览器
            browser_name = cookie_choice.replace("使用 ", "")
            browser_info = next(b for b in available_browsers if b["name"] == browser_name)

            if browser_info["platform"] == "linux":
                cookies_from_browser = browser_info["browser"]
            elif browser_info["platform"] == "windows":
                # Windows 浏览器需要转换 cookies
                console.print("[cyan]正在提取Windows浏览器Cookie...[/cyan]")
                cookie_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name

                # 根据浏览器类型选择转换函数
                if browser_info["browser"] == "firefox":
                    success = firefox_cookies_to_netscape(browser_info["profile_path"], cookie_file)
                else:
                    # Chromium-based (Edge/Chrome) - 需要解密，暂不支持自动提取
                    console.print("[yellow]Edge/Chrome Cookie 使用 DPAPI 加密，无法在 WSL2 中直接提取[/yellow]")
                    console.print("[yellow]请使用「从文件导入Cookie」选项[/yellow]")
                    cookie_file = None
                    success = False

                if not success:
                    cookie_file = None

        elif cookie_choice == "从文件导入Cookie":
            cookie_path = questionary.text("请输入Cookie文件路径 (Netscape格式):").ask()
            if cookie_path and os.path.exists(cookie_path.strip()):
                cookie_file = cookie_path.strip()
                console.print(f"[green]已加载Cookie文件: {cookie_file}[/green]")
            else:
                console.print("[red]文件不存在或路径无效[/red]")
                cookie_file = None

        elif cookie_choice == "查看Cookie获取帮助":
            console.print(COOKIE_HELP_TEXT)
            # 重新选择
            cookie_choice2 = questionary.select(
                "Cookie设置:",
                choices=cookie_choices,
            ).ask()
            if cookie_choice2 is None or cookie_choice2.startswith("查看"):
                console.print("[red]已取消[/red]")
                return
            # 递归处理... 简化处理：不使用cookie
            cookie_file = None

    console.print("\n[cyan]正在获取视频信息...[/cyan]")
    try:
        info = fetch_video_info(url, cookies_from_browser, cookie_file)
    except Exception as e:
        err_msg = str(e)
        if "cookie" in err_msg.lower():
            console.print(f"[red]Cookie加载失败:[/red] {err_msg}")
            console.print("[yellow]尝试不使用Cookie继续...[/yellow]\n")
            try:
                info = fetch_video_info(url, None, None)
            except Exception as e2:
                console.print(f"[red]获取视频信息失败:[/red] {e2}")
                return
        else:
            console.print(f"[red]获取视频信息失败:[/red] {e}")
            return

    display_video_info(info)

    mode = questionary.select(
        "选择提取类型:",
        choices=["仅提取音频", "仅下载视频", "音视频同时提取"],
    ).ask()
    if not mode:
        console.print("[red]已取消[/red]")
        return

    output_dir = questionary.text("保存目录:", default=default_output_dir or ".").ask()
    if not output_dir:
        console.print("[red]已取消[/red]")
        return
    output_dir = output_dir.strip() or "."

    if mode in ("仅提取音频", "音视频同时提取"):
        # 查找默认音频格式对应的显示名
        audio_default_key = next(
            (k for k, v in AUDIO_FORMATS.items() if v == default_audio_fmt), "MP3"
        )
        format_choice = questionary.select(
            "选择音频格式:",
            choices=list(AUDIO_FORMATS.keys()),
            default=audio_default_key,
        ).ask()
        if not format_choice:
            console.print("[red]已取消[/red]")
            return

        quality_choice = questionary.select(
            "选择音频质量:",
            choices=list(AUDIO_QUALITIES.keys()),
            default="高质量 (VBR 2)",
        ).ask()
        if not quality_choice:
            console.print("[red]已取消[/red]")
            return

        console.print()
        try:
            download_audio(
                url,
                AUDIO_FORMATS[format_choice],
                AUDIO_QUALITIES[quality_choice],
                output_dir,
                cookies_from_browser,
                cookie_file,
            )
            audio_file = find_downloaded_file(output_dir)
            if audio_file:
                size = format_size(os.path.getsize(audio_file))
                console.print(f"\n[bold green]音频下载完成![/bold green] 保存至: {audio_file} ({size})")
        except Exception as e:
            console.print(f"\n[red]音频下载失败:[/red] {e}")

    if mode in ("仅下载视频", "音视频同时提取"):
        # 查找默认视频格式对应的显示名
        video_default_key = next(
            (k for k, v in VIDEO_FORMATS.items() if v == default_video_fmt), "MP4"
        )
        format_choice = questionary.select(
            "选择视频格式:",
            choices=list(VIDEO_FORMATS.keys()),
            default=video_default_key,
        ).ask()
        if not format_choice:
            console.print("[red]已取消[/red]")
            return

        console.print()
        try:
            download_video(
                url,
                VIDEO_FORMATS[format_choice],
                output_dir,
                cookies_from_browser,
                cookie_file,
            )
            video_file = find_downloaded_file(output_dir)
            if video_file:
                size = format_size(os.path.getsize(video_file))
                console.print(f"\n[bold green]视频下载完成![/bold green] 保存至: {video_file} ({size})")
        except Exception as e:
            console.print(f"\n[red]视频下载失败:[/red] {e}")

    console.print("\n[bold green]全部完成！[/bold green]")

    # 清理临时 cookie 文件 (仅删除脚本自动创建的临时文件)
    if cookie_file and cookie_file.startswith(tempfile.gettempdir()) and os.path.exists(cookie_file):
        os.unlink(cookie_file)


if __name__ == "__main__":
    main()
