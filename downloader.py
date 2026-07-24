import asyncio
import os
import re
import random
import yt_dlp
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from config import MAX_FILE_SIZE, SUPPORTED_PLATFORMS

# ==========================================
# КУКИ — АВТОМАТИЧЕСКИ ПОДГРУЖАЮТСЯ
# ==========================================
COOKIES_FILE = "DeepLegs" if os.path.exists("DeepLegs") else None

if COOKIES_FILE:
    print(f"🍪 Куки загружены из файла: {COOKIES_FILE}")
else:
    print("⚠️ DeepLegs не найден. YouTube может не работать.")

# ==========================================
# 🧠 ФУНКЦИЯ ПОЛУЧЕНИЯ СВЕЖИХ КУК (ytc + Playwright)
# ==========================================
def get_youtube_cookies() -> dict:
    """
    Пытается получить свежие куки для YouTube.
    Сначала пробует ytc, потом файл, потом Playwright.
    Возвращает словарь с куками или None.
    """
    try:
        import ytc
        cookies_str = ytc.youtube()
        if cookies_str:
            print("🍪 Куки обновлены через ytc")
            return {'http_headers': {'Cookie': cookies_str}}
    except Exception as e:
        print(f"⚠️ ytc не сработал: {e}")
    
    if COOKIES_FILE:
        try:
            with open(COOKIES_FILE, 'r') as f:
                cookies_str = f.read().strip()
                if cookies_str:
                    print(f"🍪 Куки загружены из файла: {COOKIES_FILE}")
                    return {'cookiefile': COOKIES_FILE}
        except:
            pass
    
    # Резерв: попытка через Playwright (если файла нет или он устарел)
    try:
        import subprocess
        result = subprocess.run(
            ['python', 'cookie_updater.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and os.path.exists(COOKIES_FILE):
            print("🍪 Куки обновлены через Playwright")
            return {'cookiefile': COOKIES_FILE}
    except Exception as e:
        print(f"⚠️ Playwright не сработал: {e}")
    
    return None

# ==========================================
# 🌍 ПРОКСИ (из переменных окружения)
# ==========================================
PROXY_URL = os.getenv("PROXY_URL")  # http://user:pass@host:port

# ==========================================
# СПИСОК USER-AGENT ДЛЯ РОТАЦИИ
# ==========================================
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
]

# ==========================================
# ОПРЕДЕЛЕНИЕ ПЛАТФОРМЫ ПО ССЫЛКЕ
# ==========================================
def detect_platform(url: str) -> str:
    for platform in SUPPORTED_PLATFORMS:
        if platform in url.lower():
            return platform
    return "unknown"

# ==========================================
# 🔥 ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ КАЧЕСТВ (SD, HD, FULL HD)
# ==========================================
def get_format_for_quality(quality: str) -> str:
    """
    Возвращает формат для yt-dlp в зависимости от качества.
    """
    quality_formats = {
        "sd": 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[filesize<50M]',
        "hd": 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[filesize<100M]',
        "fullhd": 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[filesize<200M]',
        "best": 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    }
    return quality_formats.get(quality, quality_formats["best"])

# ==========================================
# ОСНОВНАЯ ФУНКЦИЯ ЗАГРУЗКИ (С ПОДДЕРЖКОЙ КАЧЕСТВА)
# ==========================================
def _sync_download(url: str, output_path: str, quality: str = "best") -> bool:
    """
    Синхронная загрузка медиа с поддержкой качества.
    quality: sd, hd, fullhd, best
    """
    platform = detect_platform(url)
    print(f"🔍 [DEBUG] Платформа определена: {platform}")
    print(f"🎬 [DEBUG] Качество: {quality}")
    
    # Получаем формат для качества
    format_str = get_format_for_quality(quality)
    
    # Базовые опции
    ydl_opts = {
        'format': format_str,
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'max_filesize': MAX_FILE_SIZE,
        'concurrent_fragment_downloads': 5,
        'socket_timeout': 30,
        'retries': 15,
        'fragment_retries': 15,
        'skip_unavailable_fragments': True,
        'ignoreerrors': True,
        'extract_flat': False,
        'prefer_ffmpeg': True,
        'ffmpeg_location': '/usr/bin/ffmpeg' if os.name != 'nt' else None,
        'sleep_interval': 1,
        'max_sleep_interval': 5,
        'sleep_interval_requests': 1,
        'user_agent': random.choice(USER_AGENTS),
    }
    
    # 🔥 ДОБАВЛЯЕМ ПРОКСИ (если есть)
    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL
        print(f"🌍 Используется прокси: {PROXY_URL}")
    
    # 🍪 ОБНОВЛЯЕМ КУКИ ДЛЯ YOUTUBE
    if platform in ["youtube.com", "youtu.be"]:
        cookies = get_youtube_cookies()
        if cookies:
            ydl_opts.update(cookies)
        
        # Специальные заголовки для YouTube
        ydl_opts['http_headers'] = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
    
    # 🔥 ОПЦИИ ДЛЯ КОНКРЕТНЫХ ПЛАТФОРМ
    if platform == "tiktok.com":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
        if COOKIES_FILE:
            ydl_opts['cookiefile'] = COOKIES_FILE
    
    elif platform in ["instagram.com", "facebook.com"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    
    elif platform in ["youtube.com", "youtu.be"]:
        # Уже настроено выше
        pass
    
    elif platform == "pinterest.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
    
    elif platform in ["twitter.com", "x.com"]:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
    
    elif platform in ["reddit.com", "vimeo.com"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
        })
    
    elif platform == "t.me":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
    
    elif platform in ["vk.com", "vkontakte.ru"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    
    elif platform == "likee.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
    
    elif platform == "rutube.ru":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    
    elif platform == "twitch.tv":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    
    elif platform == "coub.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
    
    elif platform == "tumblr.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
    
    elif platform == "dailymotion.com":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })
    
    elif platform == "9gag.com":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })
    
    try:
        print(f"📥 [DEBUG] Начинаю скачивание с {platform}: {url}", flush=True)
        
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
        
        # 🔥 АЛЬТЕРНАТИВНЫЙ ФОРМАТ
        try:
            print("🔄 Пробуем альтернативный формат...", flush=True)
            fallback_opts = ydl_opts.copy()
            fallback_opts['format'] = 'best'
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e2:
            print(f"❌ Альтернативная загрузка не удалась: {e2}", flush=True)
            
            # 🍪 РЕЗЕРВ: ПОПЫТКА ЧЕРЕЗ API ДЛЯ TIKTOK
            if platform == "tiktok.com":
                print("🔄 Пробуем скачать через альтернативный API...", flush=True)
                try:
                    import requests
                    api_url = f"https://www.tikwm.com/api/?url={url}"
                    response = requests.get(api_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("code") == 0:
                            video_url = data["data"]["play"]
                            import urllib.request
                            urllib.request.urlretrieve(video_url, output_path)
                            return os.path.exists(output_path)
                except Exception as e3:
                    print(f"❌ Альтернативный API не сработал: {e3}")
            
            return False
            
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}", flush=True)
        return False

# ==========================================
# АСИНХРОННАЯ ОБЁРТКА (С ПОДДЕРЖКОЙ КАЧЕСТВА)
# ==========================================
async def download_media(url: str, output_path: str, quality: str = "best") -> bool:
    """
    Асинхронная загрузка медиа с поддержкой множества платформ.
    quality: sd, hd, fullhd, best
    """
    print(f"🚀 [DEBUG] download_media вызвана для: {url}, качество: {quality}")
    return await asyncio.to_thread(_sync_download, url, output_path, quality)

# ==========================================
# 🔥 ИЗВЛЕЧЕНИЕ ИНФОРМАЦИИ О ВИДЕО (УЛУЧШЕННАЯ)
# ==========================================
def extract_video_info(url: str) -> dict:
    """
    Извлекает информацию о видео без скачивания.
    Возвращает: {title, duration, views, likes, uploader, thumbnail, platform}
    Теперь использует куки для всех платформ!
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'user_agent': random.choice(USER_AGENTS),
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        }
    }
    
    # 🔥 ДОБАВЛЯЕМ КУКИ ДЛЯ ВСЕХ ПЛАТФОРМ
    if COOKIES_FILE:
        ydl_opts['cookiefile'] = COOKIES_FILE
    
    # 🔥 ДЛЯ YOUTUBE ДОБАВЛЯЕМ ДОПОЛНИТЕЛЬНЫЕ ЗАГОЛОВКИ
    if "youtube.com" in url or "youtu.be" in url:
        ydl_opts['http_headers'].update({
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return get_empty_info(url)
            
            # Пробуем извлечь данные
            title = info.get('title', info.get('fulltitle', 'Неизвестно'))
            duration = info.get('duration', 0)
            view_count = info.get('view_count', 0)
            like_count = info.get('like_count', 0)
            uploader = info.get('uploader', info.get('channel', 'Неизвестно'))
            thumbnail = info.get('thumbnail', None)
            extractor = info.get('extractor', 'unknown')
            
            # 🔥 ЕСЛИ НЕТ НАЗВАНИЯ — ПЫТАЕМСЯ ПОЛУЧИТЬ ЧЕРЕЗ ALTERNATIVE
            if title == 'Неизвестно' or not title:
                title = info.get('description', 'Видео')[:50]
            
            # 🔥 ЕСЛИ ВСЁ РАВНО НЕТ — ПЫТАЕМСЯ ИЗВЛЕЧЬ ИЗ URL
            if title == 'Видео' or not title:
                title = extract_title_from_url(url)
            
            return {
                "title": title,
                "duration": duration,
                "views": view_count,
                "likes": like_count,
                "uploader": uploader,
                "thumbnail": thumbnail,
                "platform": detect_platform(url),
                "extractor": extractor
            }
            
    except yt_dlp.utils.DownloadError as e:
        print(f"❌ Ошибка извлечения информации: {e}", flush=True)
        return get_empty_info(url)
    except Exception as e:
        print(f"❌ Ошибка извлечения информации: {e}", flush=True)
        return get_empty_info(url)

def extract_title_from_url(url: str) -> str:
    """Пытается извлечь название из URL"""
    platform = detect_platform(url)
    
    if "youtube.com" in url or "youtu.be" in url:
        # Пытаемся найти ID видео
        match = re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", url)
        if match:
            video_id = match.group(1)
            return f"YouTube видео {video_id}"
        return "YouTube видео"
    
    elif "tiktok.com" in url:
        match = re.search(r"/video/(\d+)", url)
        if match:
            video_id = match.group(1)
            return f"TikTok видео {video_id}"
        return "TikTok видео"
    
    elif "instagram.com" in url:
        match = re.search(r"/reel/([^/?]+)", url)
        if match:
            video_id = match.group(1)
            return f"Instagram Reel {video_id}"
        return "Instagram видео"
    
    elif "pinterest.com" in url:
        return "Pinterest видео"
    
    elif "twitter.com" in url or "x.com" in url:
        return "Twitter/X видео"
    
    elif "facebook.com" in url:
        return "Facebook видео"
    
    elif "reddit.com" in url:
        return "Reddit видео"
    
    elif "vimeo.com" in url:
        match = re.search(r"/(\d+)", url)
        if match:
            video_id = match.group(1)
            return f"Vimeo видео {video_id}"
        return "Vimeo видео"
    
    return "Видео"

def get_empty_info(url: str) -> dict:
    """Возвращает пустую информацию о видео"""
    return {
        "title": extract_title_from_url(url),
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
async def download_media_with_progress(url: str, output_path: str, progress_callback, quality: str = "best") -> bool:
    def _sync_with_progress():
        format_str = get_format_for_quality(quality)
        ydl_opts = {
            'format': format_str,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'max_filesize': MAX_FILE_SIZE,
            'concurrent_fragment_downloads': 5,
            'socket_timeout': 10,
            'retries': 10,
            'fragment_retries': 10,
            'user_agent': random.choice(USER_AGENTS),
            'progress_hooks': [lambda d: progress_callback(
                percent=d.get('_percent_str', '0%').strip(),
                speed=d.get('_speed_str', '0'),
                eta=d.get('_eta_str', 'unknown')
            )],
        }
        if "youtube.com" in url or "youtu.be" in url:
            if COOKIES_FILE:
                ydl_opts['cookiefile'] = COOKIES_FILE
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
    try:
        info = await asyncio.to_thread(extract_video_info, url)
        return info.get("extractor") != "unknown"
    except Exception:
        return False

# ==========================================
# ЗАГРУЗКА В ВЫСОКОМ КАЧЕСТВЕ (DEPRECATED)
# ==========================================
async def download_media_hq(url: str, output_path: str) -> bool:
    """Используй download_media(url, output_path, 'fullhd') вместо этого"""
    return await download_media(url, output_path, "fullhd")

# ==========================================
# ЗАГРУЗКА ТОЛЬКО АУДИО
# ==========================================
async def download_audio(url: str, output_path: str) -> bool:
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
            'user_agent': random.choice(USER_AGENTS),
        }
        if "youtube.com" in url or "youtu.be" in url:
            if COOKIES_FILE:
                ydl_opts['cookiefile'] = COOKIES_FILE
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path.replace('.mp4', '.mp3'))
        except Exception as e:
            print(f"❌ Ошибка загрузки аудио: {e}", flush=True)
            return False
    return await asyncio.to_thread(_sync_audio)

# ==========================================
# 🔥 ЗАГРУЗКА С РОТАЦИЕЙ USER-AGENT
# ==========================================
async def download_media_rotating(url: str, output_path: str, quality: str = "best") -> bool:
    def _sync_rotating():
        ua = random.choice(USER_AGENTS)
        format_str = get_format_for_quality(quality)
        ydl_opts = {
            'format': format_str,
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
        }
        if "youtube.com" in url or "youtu.be" in url:
            if COOKIES_FILE:
                ydl_opts['cookiefile'] = COOKIES_FILE
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки с ротацией: {e}", flush=True)
            return False
    return await asyncio.to_thread(_sync_rotating)

# ==========================================
# 🔥 ДОПОЛНИТЕЛЬНАЯ: ПОЛУЧЕНИЕ ДОСТУПНЫХ КАЧЕСТВ
# ==========================================
def get_available_qualities(url: str) -> list:
    """
    Возвращает список доступных качеств для видео.
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        if "youtube.com" in url or "youtu.be" in url:
            if COOKIES_FILE:
                ydl_opts['cookiefile'] = COOKIES_FILE
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return ["sd"]
            
            # Проверяем доступные форматы
            formats = info.get('formats', [])
            heights = set()
            for f in formats:
                height = f.get('height', 0)
                if height > 0:
                    heights.add(height)
            
            qualities = []
            if any(h <= 480 for h in heights):
                qualities.append("sd")
            if any(480 < h <= 720 for h in heights):
                qualities.append("hd")
            if any(h > 720 for h in heights):
                qualities.append("fullhd")
            
            return qualities if qualities else ["sd"]
            
    except Exception as e:
        print(f"❌ Ошибка получения качеств: {e}", flush=True)
        return ["sd"]
