#!/usr/bin/env python3
"""从B站视频链接提取音频，自动搜索歌词和专辑封面并嵌入 FLAC 文件。"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yt_dlp
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3NoHeaderError


def fetch_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def clean_title(raw_title: str, uploader: str) -> tuple[str, str]:
    """从B站视频标题清洗出歌名和歌手。"""
    title = raw_title
    # 去除常见B站标题装饰（按顺序处理）
    patterns = [
        r"【.*?】", r"\[.*?\]", r"「.*?」",
        r"《.*?》(?=\s*《)",  # 连续书名号只去掉多余的
        r"（.*?）", r"\(.*?\)",
        r"\d+[Kk]\s*", r"[Hh][Dd]\b", r"[Mm][Vv]\b",
        r"官方(?:版|MV)?", r"高清", r"无损", r"蓝光",
        r"竖屏版", r"现场版", r"[Ll]ive版?", r"演唱会版",
        r"｜.*$", r"\|.*$",
    ]
    for p in patterns:
        title = re.sub(p, "", title)
    title = re.sub(r"\s+", " ", title).strip()

    # 尝试用常见分隔符拆分歌手 - 歌名
    for sep in [" - ", " — ", " – ", "-"]:
        if sep in title:
            parts = title.split(sep, 1)
            if len(parts) == 2 and all(len(p.strip()) > 0 for p in parts):
                artist, track = parts[0].strip(), parts[1].strip()
                return track, artist

    # 用 uploader 作为歌手候选
    return title, uploader


def search_lyrics(track: str, artist: str) -> tuple[str | None, str | None]:
    """从 LRCLIB 搜索歌词。返回 (synced_lyrics, plain_lyrics)。"""
    params = urllib.parse.urlencode({"track_name": track, "artist_name": artist})
    url = f"https://lrclib.net/api/search?{params}"
    try:
        results = fetch_json(url)
    except Exception as e:
        print(f"  歌词搜索失败: {e}")
        return None, None

    if not results:
        return None, None

    # 简单匹配：选第一个结果
    best = results[0]
    synced = best.get("syncedLyrics")
    plain = best.get("plainLyrics")
    match_info = f"{best.get('trackName', '?')} - {best.get('artistName', '?')}"
    print(f"  歌词匹配: {match_info}")
    return synced, plain


def search_cover(track: str, artist: str) -> bytes | None:
    """从 iTunes Search API 搜索专辑封面。"""
    query = urllib.parse.quote(f"{track} {artist}")
    url = f"https://itunes.apple.com/search?term={query}&limit=1&country=CN&media=music"
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"  封面搜索失败: {e}")
        return None

    results = data.get("results", [])
    if not results:
        return None

    artwork_url = results[0].get("artworkUrl100", "")
    if not artwork_url:
        return None

    # 替换为 600x600 高清封面
    artwork_url = artwork_url.replace("100x100bb", "600x600bb")
    print(f"  封面匹配: {results[0].get('trackName', '?')} - {results[0].get('artistName', '?')}")
    try:
        req = urllib.request.Request(artwork_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"  封面下载失败: {e}")
        return None


def download_thumbnail(url: str) -> bytes | None:
    """下载B站视频缩略图作为封面 fallback。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


def embed_metadata(flac_path: str, lyrics: str | None, cover: bytes | None,
                   title: str | None, artist: str | None):
    """将歌词和封面嵌入 FLAC 文件。"""
    audio = FLAC(flac_path)

    if title:
        audio["title"] = title
    if artist:
        audio["artist"] = artist

    if lyrics:
        audio["lyrics"] = lyrics

    if cover:
        pic = Picture()
        pic.type = 3  # Cover (front)
        pic.mime = "image/jpeg"
        pic.desc = "Cover"
        pic.data = cover
        audio.clear_pictures()
        audio.add_picture(pic)

    audio.save()


def extract_audio(url: str, output_dir: str = ".") -> tuple[str, dict]:
    """用 yt-dlp 提取音频并返回 (文件路径, 视频元数据)。"""
    meta_holder: dict = {}

    def progress_hook(d):
        if d["status"] == "finished":
            print(f"  音频下载完成，正在转换为 FLAC...")

    def info_hook(d):
        meta_holder.update(d)

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "flac",
            "preferredquality": "0",
        }],
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [info_hook],
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        meta_holder.update(info)

    # 找到生成的 flac 文件
    raw_title = info.get("title", "unknown")
    # yt-dlp 会清理文件名中的特殊字符
    tmp_filepath = ydl.prepare_filename(info)
    flac_path = os.path.splitext(tmp_filepath)[0] + ".flac"

    if not os.path.exists(flac_path):
        # 退而查找目录中最新的 flac 文件
        flac_files = sorted(Path(output_dir).glob("*.flac"), key=os.path.getmtime, reverse=True)
        if flac_files:
            flac_path = str(flac_files[0])
        else:
            raise FileNotFoundError("未找到输出的 FLAC 文件")

    return flac_path, info


def main():
    parser = argparse.ArgumentParser(description="从B站视频提取音频，嵌入歌词和封面")
    parser.add_argument("url", help="B站视频链接")
    parser.add_argument("-o", "--output", default=".", help="输出目录")
    parser.add_argument("-n", "--name", help="手动指定歌曲名")
    parser.add_argument("-a", "--artist", help="手动指定歌手名")
    parser.add_argument("-l", "--lyrics", help="手动指定歌词文件路径")
    args = parser.parse_args()

    print(f"[1/4] 提取音频...")
    flac_path, info = extract_audio(args.url, args.output)
    raw_title = info.get("title", "unknown")
    uploader = info.get("uploader", "unknown")
    thumbnail = info.get("thumbnail", "")
    print(f"  文件: {flac_path}")
    print(f"  标题: {raw_title}")
    print(f"  UP主: {uploader}")

    # 确定歌曲名和歌手
    if args.name and args.artist:
        track, artist = args.name, args.artist
    else:
        track, artist = clean_title(raw_title, uploader)
    print(f"\n[2/4] 搜索歌曲信息...")
    print(f"  歌名: {track}")
    print(f"  歌手: {artist}")

    # 搜索歌词
    print(f"\n[3/4] 搜索歌词...")
    synced_lyrics, plain_lyrics = None, None
    if args.lyrics:
        with open(args.lyrics, encoding="utf-8") as f:
            synced_lyrics = f.read()
        print(f"  使用本地歌词文件: {args.lyrics}")
    else:
        synced_lyrics, plain_lyrics = search_lyrics(track, artist)

    lyrics_text = synced_lyrics or plain_lyrics
    if lyrics_text:
        print(f"  已获取歌词 ({len(lyrics_text)} 字符)")
    else:
        print("  未找到歌词")

    # 搜索封面
    print(f"\n[4/4] 搜索封面...")
    cover = search_cover(track, artist)
    if not cover and thumbnail:
        print("  使用B站视频封面作为替代")
        cover = download_thumbnail(thumbnail)

    if cover:
        print(f"  封面已获取 ({len(cover)} 字节)")
    else:
        print("  未找到封面")

    # 嵌入元数据
    print(f"\n写入元数据...")
    embed_metadata(flac_path, lyrics_text, cover, track, artist)

    # 重命名为 歌名 - 歌手.flac
    output_dir = os.path.dirname(flac_path) or "."
    safe_name = re.sub(r'[\\/:*?"<>|]', '', f"{track} - {artist}")
    new_path = os.path.join(output_dir, f"{safe_name}.flac")
    if new_path != flac_path:
        if os.path.exists(new_path):
            os.remove(new_path)
        os.rename(flac_path, new_path)
        flac_path = new_path

    print(f"\n✅ 完成! 文件: {flac_path}")


if __name__ == "__main__":
    main()
