import asyncio
import os
import re
import random
import yt_dlp
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from config import MAX_FILE_SIZE, SUPPORTED_PLATFORMS

# ==========================================
# ОПРЕДЕЛЕНИЕ ПЛАТФОРМЫ ПО ССЫЛКЕ
# ==========================================
def detect_platform(url: str) -> str:
    for platform in SUPPORTED_PLATFORMS:
        if platform in url.lower():
            return platform
    return "unknown"

# ==========================================
# ОСНОВНАЯ ФУНКЦИЯ ЗАГРУЗКИ
# ==========================================
def _sync_download(url: str, output_path: str) -> bool:
    platform = detect_platform(url)
    
    # Базовые опции
    ydl_opts = {
        'format': 'b[ext=mp4][filesize<50M]/best[ext=mp4][filesize<50M]/best[filesize<50M]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'max_filesize': MAX_FILE_SIZE,
        'concurrent_fragment_downloads': 5,
        'socket_timeout': 10,
    }
    
    # 🔥 ОПЦИИ ДЛЯ КОНКРЕТНЫХ ПЛАТФОРМ
    if platform == "tiktok.com":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'cookiesfrombrowser': ('chrome',),
        })
    
    elif platform in ["instagram.com", "facebook.com"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    elif platform in ["youtube.com", "youtu.be"]:
        ydl_opts.update({
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            'cookiesfrombrowser': ('chrome',),
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
        })
    
    elif platform == "pinterest.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    elif platform in ["twitter.com", "x.com"]:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'cookiesfrombrowser': ('chrome',),
        })
    
    elif platform in ["reddit.com", "vimeo.com"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
        })
    
    elif platform == "t.me":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    # 🌍 НОВЫЕ ПЛАТФОРМЫ
    elif platform in ["vk.com", "vkontakte.ru"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'cookiesfrombrowser': ('chrome',),
        })
    
    elif platform == "likee.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    elif platform == "rutube.ru":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    elif platform == "twitch.tv":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'cookiesfrombrowser': ('chrome',),
        })
    
    elif platform == "coub.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    elif platform == "tumblr.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    elif platform == "dailymotion.com":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    elif platform == "9gag.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    # 🔥 УНИВЕРСАЛЬНЫЕ ОПЦИИ
    ydl_opts.update({
        'retries': 10,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'ignoreerrors': True,
        'extract_flat': False,
        'prefer_ffmpeg': True,
        'ffmpeg_location': '/usr/bin/ffmpeg' if os.name != 'nt' else None,
    })
    
    try:
        print(f"📥 Скачивание с {platform}: {url}", flush=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Загрузка завершена! Размер: {file_size:.2f} МБ", flush=True)
            return True
        else:
            print(f"❌ Файл не найден: {output_path}", flush=True)
            return False
            
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ Ошибка yt-dlp: {e}", flush=True)
        try:
            print("🔄 Пробуем альтернативный формат...", flush=True)
            fallback_opts = ydl_opts.copy()
            fallback_opts['format'] = 'best'
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e2:
            print(f"❌ Альтернативная загрузка не удалась: {e2}", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}", flush=True)
        return False

# ==========================================
# АСИНХРОННАЯ ОБЁРТКА
# ==========================================
async def download_media(url: str, output_path: str) -> bool:
    """
    Асинхронная загрузка медиа с поддержкой множества платформ.
    """
    return await asyncio.to_thread(_sync_download, url, output_path)

# ==========================================
# ИЗВЛЕЧЕНИЕ ИНФОРМАЦИИ О ВИДЕО
# ==========================================
def extract_video_info(url: str) -> dict:
    """
    Извлекает информацию о видео без скачивания.
    Возвращает: {title, duration, views, likes, uploader, thumbnail}
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'cookiesfrombrowser': ('chrome',),
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Неизвестно"),
                "duration": info.get("duration", 0),
                "views": info.get("view_count", 0),
                "likes": info.get("like_count", 0),
                "uploader": info.get("uploader", "Неизвестно"),
                "thumbnail": info.get("thumbnail", None),
                "platform": detect_platform(url),
                "extractor": info.get("extractor", "unknown")
            }
    except Exception as e:
        print(f"❌ Ошибка извлечения информации: {e}", flush=True)
        return {
            "title": "Неизвестно",
            "duration": 0,
            "views": 0,
            "likes": 0,
            "uploader": "Неизвестно",
            "thumbnail": None,
            "platform": detect_platform(url),
            "extractor": "unknown"
        }

# ==========================================
# ЗАГРУЗКА С ПРОГРЕССОМ
# ==========================================
async def download_media_with_progress(url: str, output_path: str, progress_callback) -> bool:
    """
    Скачивание с отслеживанием прогресса.
    progress_callback принимает аргументы: (percent, speed, eta)
    """
    def _sync_with_progress():
        ydl_opts = {
            'format': 'b[ext=mp4][filesize<50M]/best[ext=mp4][filesize<50M]/best[filesize<50M]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'max_filesize': MAX_FILE_SIZE,
            'concurrent_fragment_downloads': 5,
            'socket_timeout': 10,
            'retries': 10,
            'fragment_retries': 10,
            'progress_hooks': [lambda d: progress_callback(
                percent=d.get('_percent_str', '0%').strip(),
                speed=d.get('_speed_str', '0'),
                eta=d.get('_eta_str', 'unknown')
            )],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}", flush=True)
            return False
    
    return await asyncio.to_thread(_sync_with_progress)

# ==========================================
# ПРОВЕРКА ВАЛИДНОСТИ ССЫЛКИ
# ==========================================
async def is_valid_url(url: str) -> bool:
    """
    Проверяет, является ли ссылка валидной для скачивания.
    """
    try:
        info = await asyncio.to_thread(extract_video_info, url)
        return info.get("extractor") != "unknown"
    except Exception:
        return False

# ==========================================
# ЗАГРУЗКА В ВЫСОКОМ КАЧЕСТВЕ
# ==========================================
async def download_media_hq(url: str, output_path: str) -> bool:
    """
    Скачивает видео в наилучшем доступном качестве.
    """
    def _sync_hq():
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'max_filesize': 100 * 1024 * 1024,
            'concurrent_fragment_downloads': 5,
            'socket_timeout': 10,
            'retries': 10,
            'fragment_retries': 10,
            'cookiesfrombrowser': ('chrome',),
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e:
            print(f"❌ Ошибка HQ загрузки: {e}", flush=True)
            return False
    
    return await asyncio.to_thread(_sync_hq)

# ==========================================
# ЗАГРУЗКА ТОЛЬКО АУДИО
# ==========================================
async def download_audio(url: str, output_path: str) -> bool:
    """
    Скачивает только аудиодорожку в MP3.
    """
    def _sync_audio():
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path.replace('.mp4', '.mp3'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'socket_timeout': 10,
            'retries': 10,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path.replace('.mp4', '.mp3'))
        except Exception as e:
            print(f"❌ Ошибка загрузки аудио: {e}", flush=True)
            return False
    
    return await asyncio.to_thread(_sync_audio)

# ==========================================
# 🔥 НОВАЯ ФУНКЦИЯ: ЗАГРУЗКА С ROTATING USER-AGENT
# ==========================================
async def download_media_rotating(url: str, output_path: str) -> bool:
    """
    Скачивание с ротацией User-Agent для обхода блокировок.
    """
    def _sync_rotating():
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/117.0',
            'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
        ]
        ua = random.choice(user_agents)
        
        ydl_opts = {
            'format': 'b[ext=mp4][filesize<50M]/best[ext=mp4][filesize<50M]/best[filesize<50M]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'max_filesize': MAX_FILE_SIZE,
            'concurrent_fragment_downloads': 5,
            'socket_timeout': 10,
            'user_agent': ua,
            'retries': 15,
            'fragment_retries': 15,
            'cookiesfrombrowser': ('chrome',),
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки с ротацией: {e}", flush=True)
            return False
    
    return await asyncio.to_thread(_sync_rotating)
