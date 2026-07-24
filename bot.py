import asyncio
import os
import random
import yt_dlp
from aiohttp import web

# ==========================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не падал по порту)
# ==========================================
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_head("/", handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Веб-сервер успешно запущен на порту {port}")

# ==========================================
# НАСТРОЙКИ (перенесены из config)
# ==========================================
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 МБ в байтах
SUPPORTED_PLATFORMS = [
    "tiktok.com", "instagram.com", "facebook.com", "youtube.com", "youtu.be",
    "pinterest.com", "twitter.com", "x.com", "reddit.com", "vimeo.com", "t.me",
    "vk.com", "vkontakte.ru", "likee.com", "rutube.ru", "twitch.tv", "coub.com",
    "tumblr.com", "dailymotion.com", "9gag.com"
]

# ==========================================
# КУКИ — АВТОМАТИЧЕСКИ ПОДГРУЖАЮТСЯ
# ==========================================
COOKIES_FILE = "DeepLegs" if os.path.exists("DeepLegs") else None

if COOKIES_FILE:
    print(f"🍪 Куки загружены: {COOKIES_FILE}")
else:
    print("⚠️ DeepLegs не найден. YouTube может не работать.")

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
# ОСНОВНАЯ ФУНКЦИЯ ЗАГРУЗКИ
# ==========================================
def _sync_download(url: str, output_path: str) -> bool:
    platform = detect_platform(url)
    
    ydl_opts = {
        'format': 'b[ext=mp4][filesize<50M]/best[ext=mp4][filesize<50M]/best[filesize<50M]/best',
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
    }
    
    if platform == "tiktok.com":
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})
    
    elif platform in ["instagram.com", "facebook.com"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': random.choice(USER_AGENTS),
        })
    
    elif platform in ["youtube.com", "youtu.be"]:
        ydl_opts.update({
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            'user_agent': random.choice(USER_AGENTS),
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
        })
        if COOKIES_FILE:
            ydl_opts['cookiefile'] = COOKIES_FILE
    
    elif platform == "pinterest.com":
        ydl_opts.update({'format': 'best[ext=mp4]/best', 'user_agent': random.choice(USER_AGENTS)})
    
    elif platform in ["twitter.com", "x.com"]:
        ydl_opts.update({'format': 'best[ext=mp4]/best'})
    
    elif platform in ["reddit.com", "vimeo.com"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
            'user_agent': random.choice(USER_AGENTS),
        })
    
    elif platform == "t.me":
        ydl_opts.update({'format': 'best[ext=mp4]/best', 'user_agent': random.choice(USER_AGENTS)})
    
    elif platform in ["vk.com", "vkontakte.ru"]:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': random.choice(USER_AGENTS),
        })
    
    elif platform == "likee.com":
        ydl_opts.update({'format': 'best[ext=mp4]/best', 'user_agent': random.choice(USER_AGENTS)})
    
    elif platform == "rutube.ru":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': random.choice(USER_AGENTS),
        })
    
    elif platform == "twitch.tv":
        ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})
    
    elif platform == "coub.com":
        ydl_opts.update({'format': 'best[ext=mp4]/best', 'user_agent': random.choice(USER_AGENTS)})
    
    elif platform == "tumblr.com":
        ydl_opts.update({'format': 'best[ext=mp4]/best', 'user_agent': random.choice(USER_AGENTS)})
    
    elif platform == "dailymotion.com":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'user_agent': random.choice(USER_AGENTS),
        })
    
    elif platform == "9gag.com":
        ydl_opts.update({'format': 'best[ext=mp4]/best', 'user_agent': random.choice(USER_AGENTS)})
    
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
    return await asyncio.to_thread(_sync_download, url, output_path)

# ==========================================
# ИЗВЛЕЧЕНИЕ ИНФОРМАЦИИ О ВИДЕО
# ==========================================
def extract_video_info(url: str) -> dict:
    ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
    if "youtube.com" in url or "youtu.be" in url:
        if COOKIES_FILE:
            ydl_opts['cookiefile'] = COOKIES_FILE
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
# ЗАГРУЗКА В ВЫСОКОМ КАЧЕСТВЕ
# ==========================================
async def download_media_hq(url: str, output_path: str) -> bool:
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
            'user_agent': random.choice(USER_AGENTS),
        }
        if "youtube.com" in url or "youtu.be" in url:
            if COOKIES_FILE:
                ydl_opts['cookiefile'] = COOKIES_FILE
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
async def download_media_rotating(url: str, output_path: str) -> bool:
    def _sync_rotating():
        ua = random.choice(USER_AGENTS)
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
