import asyncio
import os
import re
import random
import yt_dlp
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from config import MAX_FILE_SIZE, SUPPORTED_PLATFORMS

# ==========================================
# КУКИ — ПОЛНОСТЬЮ ОТКЛЮЧЕНЫ, ТОЛЬКО ОБХОДЫ
# ==========================================
COOKIES_FILE = None
print("⚠️ Куки ОТКЛЮЧЕНЫ — используются только обходные пути")

# ==========================================
# 🌍 ПРОКСИ (из переменных окружения)
# ==========================================
PROXY_URL = os.getenv("PROXY_URL")

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
    url_lower = url.lower()
    for platform in SUPPORTED_PLATFORMS:
        if platform in url_lower:
            return platform
    
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        
        domain_map = {
            "tiktok.com": "tiktok.com",
            "instagram.com": "instagram.com",
            "youtube.com": "youtube.com",
            "youtu.be": "youtu.be",
            "pinterest.com": "pinterest.com",
            "twitter.com": "twitter.com",
            "x.com": "x.com",
            "facebook.com": "facebook.com",
            "reddit.com": "reddit.com",
            "vimeo.com": "vimeo.com",
            "t.me": "t.me",
            "vk.com": "vk.com",
            "vkontakte.ru": "vkontakte.ru",
            "likee.com": "likee.com",
            "rutube.ru": "rutube.ru",
            "twitch.tv": "twitch.tv",
            "coub.com": "coub.com",
            "tumblr.com": "tumblr.com",
            "dailymotion.com": "dailymotion.com",
            "9gag.com": "9gag.com",
        }
        
        for key, value in domain_map.items():
            if key in domain:
                return value
    except:
        pass
    
    patterns = {
        r'tiktok\.com/@[\w\.]+/video/': 'tiktok.com',
        r'tiktok\.com/@[\w\.]+': 'tiktok.com',
        r'instagram\.com/(?:p|reel|tv)/': 'instagram.com',
        r'youtube\.com/shorts/': 'youtube.com',
        r'youtu\.be/': 'youtu.be',
        r'pinterest\.com/pin/': 'pinterest.com',
        r'twitter\.com/\w+/status/': 'twitter.com',
        r'x\.com/\w+/status/': 'x.com',
        r'facebook\.com/.*?/videos/': 'facebook.com',
        r'reddit\.com/r/.*?/comments/': 'reddit.com',
        r'vimeo\.com/\d+': 'vimeo.com',
        r't\.me/': 't.me',
        r'vk\.com/video': 'vk.com',
        r'rutube\.ru/video/': 'rutube.ru',
        r'twitch\.tv/': 'twitch.tv',
        r'dailymotion\.com/video/': 'dailymotion.com',
        r'9gag\.com/': '9gag.com',
    }
    
    for pattern, platform in patterns.items():
        if re.search(pattern, url_lower):
            return platform
    
    return "unknown"

# ==========================================
# 🔥 ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ КАЧЕСТВ
# ==========================================
def get_format_for_quality(quality: str) -> str:
    quality_formats = {
        "sd": 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[filesize<50M]',
        "hd": 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[filesize<100M]',
        "fullhd": 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[filesize<200M]',
        "best": 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    }
    return quality_formats.get(quality, quality_formats["best"])

# ==========================================
# 🔥 УНИВЕРСАЛЬНЫЙ ОБХОДНОЙ ПУТЬ
# ==========================================
def universal_fallback(url: str, output_path: str) -> bool:
    try:
        print("🔄 Универсальный обходной путь...", flush=True)
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'user_agent': random.choice(USER_AGENTS),
            'extract_flat': False,
            'socket_timeout': 20,
            'retries': 3,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_path):
            print(f"✅ Универсальный обходной путь сработал!", flush=True)
            return True
        
        import requests
        print("🔄 Пробуем прямой запрос...", flush=True)
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=20, stream=True)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'video' in content_type or 'mp4' in content_type:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return os.path.exists(output_path)
        
        return False
        
    except Exception as e:
        print(f"❌ Универсальный обходной путь не сработал: {e}", flush=True)
        return False

# ==========================================
# 🔥 ОБХОДНЫЕ ПУТИ ДЛЯ ПЛАТФОРМ
# ==========================================

def fallback_youtube(url: str, output_path: str) -> bool:
    """Обходной путь для YouTube с несколькими клиентами"""
    try:
        print("🔄 YouTube fallback...", flush=True)
        
        match = re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", url)
        if not match:
            print("❌ Не удалось извлечь ID видео")
            return False
        
        video_id = match.group(1)
        alt_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"   ID видео: {video_id}")
        
        # 🔥 МЕТОД 1: mweb клиент (мобильный сайт)
        try:
            print("   🔹 Метод 1: mweb клиент...", flush=True)
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['mweb'],
                    }
                },
                'socket_timeout': 30,
                'retries': 5,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([alt_url])
            if os.path.exists(output_path):
                print("   ✅ Метод 1 (mweb) сработал!")
                return True
        except Exception as e:
            print(f"   ❌ Метод 1 не сработал: {str(e)[:100]}", flush=True)
        
        # 🔥 МЕТОД 2: android клиент
        try:
            print("   🔹 Метод 2: android клиент...", flush=True)
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                    }
                },
                'socket_timeout': 30,
                'retries': 5,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([alt_url])
            if os.path.exists(output_path):
                print("   ✅ Метод 2 (android) сработал!")
                return True
        except Exception as e:
            print(f"   ❌ Метод 2 не сработал: {str(e)[:100]}", flush=True)
        
        # 🔥 МЕТОД 3: web клиент
        try:
            print("   🔹 Метод 3: web клиент...", flush=True)
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'user_agent': random.choice(USER_AGENTS),
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                    }
                },
                'socket_timeout': 30,
                'retries': 5,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([alt_url])
            if os.path.exists(output_path):
                print("   ✅ Метод 3 (web) сработал!")
                return True
        except Exception as e:
            print(f"   ❌ Метод 3 не сработал: {str(e)[:100]}", flush=True)
        
        # 🔥 МЕТОД 4: tv клиент (для TV)
        try:
            print("   🔹 Метод 4: tv клиент...", flush=True)
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'user_agent': 'Mozilla/5.0 (Linux; Tizen 5.5) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/4.0 Chrome/72.0.3626.121 Safari/537.36',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['tv'],
                    }
                },
                'socket_timeout': 30,
                'retries': 5,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([alt_url])
            if os.path.exists(output_path):
                print("   ✅ Метод 4 (tv) сработал!")
                return True
        except Exception as e:
            print(f"   ❌ Метод 4 не сработал: {str(e)[:100]}", flush=True)
        
        return False
        
    except Exception as e:
        print(f"❌ YouTube fallback полностью не сработал: {e}", flush=True)
        return False

def fallback_tiktok(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 TikTok fallback...", flush=True)
        
        api_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                video_url = data["data"]["play"]
                import urllib.request
                urllib.request.urlretrieve(video_url, output_path)
                return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ TikTok fallback не сработал: {e}", flush=True)
        return False

def fallback_instagram(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Instagram fallback...", flush=True)
        
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'"video_url":"([^"]+)"', response.text)
            if match:
                video_url = match.group(1).replace('\\', '')
                import urllib.request
                urllib.request.urlretrieve(video_url, output_path)
                return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Instagram fallback не сработал: {e}", flush=True)
        return False

def fallback_facebook(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Facebook fallback...", flush=True)
        
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'"playable_url":"([^"]+)"', response.text)
            if match:
                video_url = match.group(1).replace('\\', '')
                import urllib.request
                urllib.request.urlretrieve(video_url, output_path)
                return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Facebook fallback не сработал: {e}", flush=True)
        return False

def fallback_twitter(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Twitter fallback...", flush=True)
        
        api_url = f"https://twitsave.com/info?url={url}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'href="([^"]+)"[^>]*download', response.text)
            if match:
                video_url = match.group(1)
                import urllib.request
                urllib.request.urlretrieve(video_url, output_path)
                return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Twitter fallback не сработал: {e}", flush=True)
        return False

def fallback_reddit(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Reddit fallback...", flush=True)
        
        json_url = url + ".json" if not url.endswith('.json') else url
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(json_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                post = data[0].get('data', {}).get('children', [{}])[0].get('data', {})
                video_url = post.get('secure_media', {}).get('reddit_video', {}).get('fallback_url')
                if video_url:
                    import urllib.request
                    urllib.request.urlretrieve(video_url, output_path)
                    return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Reddit fallback не сработал: {e}", flush=True)
        return False

def fallback_pinterest(url: str, output_path: str) -> bool:
    try:
        import requests
        from bs4 import BeautifulSoup
        print("🔄 Pinterest fallback...", flush=True)
        
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            video_tags = soup.find_all('video')
            for video in video_tags:
                src = video.get('src')
                if src and src.startswith('http'):
                    import urllib.request
                    urllib.request.urlretrieve(src, output_path)
                    return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Pinterest fallback не сработал: {e}", flush=True)
        return False

def fallback_vimeo(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Vimeo fallback...", flush=True)
        
        match = re.search(r'/(\d+)', url)
        if match:
            video_id = match.group(1)
            api_url = f"https://vimeo.com/api/v2/video/{video_id}.json"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    video_url = data[0].get('url')
                    if video_url:
                        import urllib.request
                        urllib.request.urlretrieve(video_url, output_path)
                        return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Vimeo fallback не сработал: {e}", flush=True)
        return False

def fallback_twitch(url: str, output_path: str) -> bool:
    try:
        print("🔄 Twitch fallback...", flush=True)
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'user_agent': random.choice(USER_AGENTS),
            'socket_timeout': 20,
            'retries': 3,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.exists(output_path)
    except Exception as e:
        print(f"❌ Twitch fallback не сработал: {e}", flush=True)
        return False

def fallback_vk(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 VK fallback...", flush=True)
        
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'"url":"([^"]+)"', response.text)
            if match:
                video_url = match.group(1).replace('\\', '')
                if video_url.startswith('http'):
                    import urllib.request
                    urllib.request.urlretrieve(video_url, output_path)
                    return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ VK fallback не сработал: {e}", flush=True)
        return False

def fallback_rutube(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Rutube fallback...", flush=True)
        
        match = re.search(r'/video/(\d+)', url)
        if match:
            video_id = match.group(1)
            api_url = f"https://rutube.ru/api/play/video/{video_id}/"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                video_url = data.get('video_url')
                if video_url:
                    import urllib.request
                    urllib.request.urlretrieve(video_url, output_path)
                    return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Rutube fallback не сработал: {e}", flush=True)
        return False

def fallback_dailymotion(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Dailymotion fallback...", flush=True)
        
        match = re.search(r'/video/([^_]+)', url)
        if match:
            video_id = match.group(1)
            api_url = f"https://www.dailymotion.com/video/{video_id}"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                match = re.search(r'"video_url":"([^"]+)"', response.text)
                if match:
                    video_url = match.group(1).replace('\\', '')
                    import urllib.request
                    urllib.request.urlretrieve(video_url, output_path)
                    return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Dailymotion fallback не сработал: {e}", flush=True)
        return False

def fallback_9gag(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 9GAG fallback...", flush=True)
        
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'"video":"([^"]+)"', response.text)
            if match:
                video_url = match.group(1).replace('\\', '')
                import urllib.request
                urllib.request.urlretrieve(video_url, output_path)
                return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ 9GAG fallback не сработал: {e}", flush=True)
        return False

def fallback_telegram(url: str, output_path: str) -> bool:
    try:
        import requests
        print("🔄 Telegram fallback...", flush=True)
        
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'href="([^"]+\.mp4)"', response.text)
            if match:
                video_url = match.group(1)
                if not video_url.startswith('http'):
                    video_url = 'https://t.me' + video_url
                import urllib.request
                urllib.request.urlretrieve(video_url, output_path)
                return os.path.exists(output_path)
        
        return False
    except Exception as e:
        print(f"❌ Telegram fallback не сработал: {e}", flush=True)
        return False

# ==========================================
# ОСНОВНАЯ ФУНКЦИЯ ЗАГРУЗКИ
# ==========================================
def _sync_download(url: str, output_path: str, quality: str = "best") -> bool:
    platform = detect_platform(url)
    is_shorts = "shorts/" in url or "/shorts/" in url
    
    print(f"🔍 [DEBUG] Платформа: {platform}")
    print(f"🎬 [DEBUG] Качество: {quality}")
    
    if is_shorts:
        print(f"📱 [DEBUG] YouTube Shorts!", flush=True)
    
    format_str = get_format_for_quality(quality)
    
    ydl_opts = {
        'format': format_str,
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'max_filesize': 200 * 1024 * 1024,
        'concurrent_fragment_downloads': 10,
        'socket_timeout': 15,
        'retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'ignoreerrors': True,
        'extract_flat': False,
        'prefer_ffmpeg': True,
        'ffmpeg_location': '/usr/bin/ffmpeg' if os.name != 'nt' else None,
        'sleep_interval': 0.5,
        'max_sleep_interval': 2,
        'user_agent': random.choice(USER_AGENTS),
        'external_downloader': 'aria2c',
        'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
    }
    
    if is_shorts:
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'no_check_certificate': True,
            'prefer_insecure': True,
        })
    
    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL
    
    # 🔥 БЕЗ КУК — ТОЛЬКО ЗАГОЛОВКИ
    if platform in ["youtube.com", "youtu.be"] or is_shorts:
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
    platform_opts = {
        "tiktok.com": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "instagram.com": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "facebook.com": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "pinterest.com": {'format': 'best[ext=mp4]/best'},
        "twitter.com": {'format': 'best[ext=mp4]/best'},
        "x.com": {'format': 'best[ext=mp4]/best'},
        "reddit.com": {'format': 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best'},
        "vimeo.com": {'format': 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best'},
        "t.me": {'format': 'best[ext=mp4]/best'},
        "vk.com": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "vkontakte.ru": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "likee.com": {'format': 'best[ext=mp4]/best'},
        "rutube.ru": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "twitch.tv": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "coub.com": {'format': 'best[ext=mp4]/best'},
        "tumblr.com": {'format': 'best[ext=mp4]/best'},
        "dailymotion.com": {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
        "9gag.com": {'format': 'best[ext=mp4]/best'},
    }
    
    for key, opts in platform_opts.items():
        if key in platform:
            ydl_opts.update(opts)
            break
    
    # ==========================================
    # 🔥 5 ПОПЫТОК СКАЧИВАНИЯ
    # ==========================================
    
    # 1️⃣ СТАНДАРТНАЯ
    try:
        print(f"📥 [1] Стандартная загрузка...", flush=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            print(f"✅ Загрузка завершена!", flush=True)
            return True
    except Exception as e:
        print(f"❌ [1] Ошибка: {e}", flush=True)
    
    # 2️⃣ АЛЬТЕРНАТИВНЫЙ ФОРМАТ
    try:
        print(f"📥 [2] Альтернативный формат...", flush=True)
        fallback_opts = ydl_opts.copy()
        fallback_opts['format'] = 'best'
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            return True
    except Exception as e:
        print(f"❌ [2] Ошибка: {e}", flush=True)
    
    # 3️⃣ БЕЗ HTTP_HEADERS
    try:
        print(f"📥 [3] Без заголовков...", flush=True)
        no_headers_opts = ydl_opts.copy()
        no_headers_opts.pop('http_headers', None)
        no_headers_opts['format'] = 'best'
        with yt_dlp.YoutubeDL(no_headers_opts) as ydl:
            ydl.download([url])
        if os.path.exists(output_path):
            return True
    except Exception as e:
        print(f"❌ [3] Ошибка: {e}", flush=True)
    
    # 4️⃣ СПЕЦИАЛЬНЫЙ ОБХОДНОЙ ПУТЬ ДЛЯ ПЛАТФОРМЫ
    print(f"📥 [4] Обходной путь для {platform}...", flush=True)
    
    fallbacks = {
        "youtube.com": fallback_youtube,
        "youtu.be": fallback_youtube,
        "tiktok.com": fallback_tiktok,
        "instagram.com": fallback_instagram,
        "facebook.com": fallback_facebook,
        "twitter.com": fallback_twitter,
        "x.com": fallback_twitter,
        "reddit.com": fallback_reddit,
        "pinterest.com": fallback_pinterest,
        "vimeo.com": fallback_vimeo,
        "twitch.tv": fallback_twitch,
        "vk.com": fallback_vk,
        "vkontakte.ru": fallback_vk,
        "rutube.ru": fallback_rutube,
        "dailymotion.com": fallback_dailymotion,
        "9gag.com": fallback_9gag,
        "t.me": fallback_telegram,
    }
    
    for key, fallback_func in fallbacks.items():
        if key in platform:
            if fallback_func(url, output_path):
                return True
            break
    
    # 5️⃣ УНИВЕРСАЛЬНЫЙ ОБХОДНОЙ ПУТЬ
    print(f"📥 [5] Универсальный обходной путь...", flush=True)
    if universal_fallback(url, output_path):
        return True
    
    print(f"❌ Все попытки загрузки не удались!", flush=True)
    return False

# ==========================================
# АСИНХРОННАЯ ОБЁРТКА
# ==========================================
async def download_media(url: str, output_path: str, quality: str = "best") -> bool:
    print(f"🚀 download_media: {url}, качество: {quality}")
    return await asyncio.to_thread(_sync_download, url, output_path, quality)

# ==========================================
# 🎵 СКАЧИВАНИЕ АУДИО
# ==========================================
def _sync_download_audio(url: str, output_path: str) -> bool:
    try:
        print(f"🎵 Скачиваю аудио: {url}", flush=True)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'socket_timeout': 15,
            'retries': 3,
            'fragment_retries': 3,
            'user_agent': random.choice(USER_AGENTS),
        }
        
        if "youtube.com" in url or "youtu.be" in url:
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(output_path):
            print(f"✅ Аудио скачано: {output_path}", flush=True)
            return True
        
        print("🔄 [2] Пробуем скачать аудио без конвертации...", flush=True)
        ydl_opts_no_convert = {
            'format': 'bestaudio/best',
            'outtmpl': output_path.replace('.mp3', '.m4a'),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'socket_timeout': 15,
            'retries': 3,
            'user_agent': random.choice(USER_AGENTS),
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_no_convert) as ydl:
            ydl.download([url])
        
        m4a_path = output_path.replace('.mp3', '.m4a')
        if os.path.exists(m4a_path):
            try:
                import subprocess
                subprocess.run(['ffmpeg', '-i', m4a_path, '-acodec', 'libmp3lame', '-ab', '192k', output_path], 
                             capture_output=True, timeout=30)
                if os.path.exists(output_path):
                    os.remove(m4a_path)
                    print(f"✅ Аудио сконвертировано в MP3: {output_path}", flush=True)
                    return True
            except Exception as e:
                print(f"⚠️ Ошибка конвертации: {e}", flush=True)
                if os.path.exists(m4a_path):
                    os.rename(m4a_path, output_path)
                    return True
        
        if "youtube.com" in url or "youtu.be" in url:
            print("🔄 [3] Пробуем через альтернативный метод...", flush=True)
            try:
                alt_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio',
                    'outtmpl': output_path,
                    'quiet': True,
                    'no_warnings': True,
                    'noplaylist': True,
                    'socket_timeout': 15,
                    'retries': 3,
                    'user_agent': random.choice(USER_AGENTS),
                }
                
                with yt_dlp.YoutubeDL(alt_opts) as ydl:
                    ydl.download([url])
                
                if os.path.exists(output_path):
                    return True
            except:
                pass
        
        return False
        
    except Exception as e:
        print(f"❌ Ошибка скачивания аудио: {e}", flush=True)
        return False

async def download_audio(url: str, output_path: str) -> bool:
    print(f"🎵 download_audio: {url}")
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_sync_download_audio, url, output_path),
            timeout=60
        )
    except asyncio.TimeoutError:
        print(f"❌ Таймаут скачивания аудио (60 сек)", flush=True)
        return False

# ==========================================
# ✂️ СКАЧИВАНИЕ С ОБРЕЗКОЙ
# ==========================================
def _sync_download_with_cut(url: str, output_path: str, start_time: str = None, end_time: str = None) -> bool:
    try:
        print(f"✂️ Скачивание с обрезкой: {start_time} - {end_time}", flush=True)
        
        temp_path = output_path.replace('.mp4', '_temp.mp4')
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': temp_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'ignoreerrors': True,
            'user_agent': random.choice(USER_AGENTS),
            'socket_timeout': 15,
            'retries': 3,
            'concurrent_fragment_downloads': 10,
        }
        
        if "youtube.com" in url or "youtu.be" in url:
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if not os.path.exists(temp_path):
            return False
        
        import subprocess
        
        cmd = ['ffmpeg', '-i', temp_path]
        
        if start_time:
            cmd.extend(['-ss', start_time])
        if end_time:
            cmd.extend(['-to', end_time])
        
        cmd.extend(['-c', 'copy', '-avoid_negative_ts', '1', output_path])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"✅ Обрезка завершена!", flush=True)
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Ошибка обрезки: {e}", flush=True)
        return False

async def download_media_with_cut(url: str, output_path: str, start_time: str = None, end_time: str = None) -> bool:
    return await asyncio.to_thread(_sync_download_with_cut, url, output_path, start_time, end_time)

# ==========================================
# ИЗВЛЕЧЕНИЕ ИНФОРМАЦИИ О ВИДЕО
# ==========================================
def extract_video_info(url: str) -> dict:
    is_shorts = "shorts/" in url or "/shorts/" in url
    
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
        },
        'socket_timeout': 10,
        'retries': 2,
    }
    
    if is_shorts:
        ydl_opts.update({
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True,
        })
    
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
            
            platform = detect_platform(url)
            extractor = info.get('extractor', 'unknown')
            
            platform_map = {
                'youtube': 'youtube.com',
                'youtubedee': 'youtube.com',
                'instagram': 'instagram.com',
                'tiktok': 'tiktok.com',
                'pinterest': 'pinterest.com',
                'twitter': 'twitter.com',
                'x': 'x.com',
                'facebook': 'facebook.com',
                'reddit': 'reddit.com',
                'vimeo': 'vimeo.com',
                'telegram': 't.me',
                'vk': 'vk.com',
                'vkontakte': 'vk.com',
                'likee': 'likee.com',
                'rutube': 'rutube.ru',
                'twitch': 'twitch.tv',
                'coub': 'coub.com',
                'tumblr': 'tumblr.com',
                'dailymotion': 'dailymotion.com',
                '9gag': '9gag.com',
            }
            
            if extractor in platform_map:
                platform = platform_map[extractor]
            elif platform == 'unknown':
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
                for key, value in platform_map.items():
                    if key in domain:
                        platform = value
                        break
            
            return {
                "title": info.get('title', info.get('fulltitle', 'Неизвестно'))[:50],
                "duration": info.get('duration', 0),
                "views": info.get('view_count', 0),
                "likes": info.get('like_count', 0),
                "uploader": info.get('uploader', info.get('channel', 'Неизвестно')),
                "thumbnail": info.get('thumbnail', None),
                "platform": platform,
                "extractor": extractor
            }
    except Exception as e:
        print(f"⚠️ Ошибка извлечения: {e}", flush=True)
        return get_empty_info(url)

def get_empty_info(url: str) -> dict:
    return {
        "title": "Видео",
        "duration": 0,
        "views": 0,
        "likes": 0,
        "uploader": "Неизвестно",
        "thumbnail": None,
        "platform": detect_platform(url),
        "extractor": "unknown"
    }

# ==========================================
# ОСТАЛЬНЫЕ ФУНКЦИИ
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
            'max_filesize': 200 * 1024 * 1024,
            'concurrent_fragment_downloads': 10,
            'socket_timeout': 10,
            'retries': 3,
            'fragment_retries': 3,
            'user_agent': random.choice(USER_AGENTS),
            'progress_hooks': [lambda d: progress_callback(
                percent=d.get('_percent_str', '0%').strip(),
                speed=d.get('_speed_str', '0'),
                eta=d.get('_eta_str', 'unknown')
            )],
        }
        if "youtube.com" in url or "youtu.be" in url:
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
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}", flush=True)
            return False
    return await asyncio.to_thread(_sync_with_progress)

async def is_valid_url(url: str) -> bool:
    try:
        info = await asyncio.to_thread(extract_video_info, url)
        return info.get("extractor") != "unknown" and info.get("platform") != "unknown"
    except Exception:
        return False

async def download_media_hq(url: str, output_path: str) -> bool:
    return await download_media(url, output_path, "fullhd")

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
            'max_filesize': 200 * 1024 * 1024,
            'concurrent_fragment_downloads': 10,
            'socket_timeout': 10,
            'user_agent': ua,
            'retries': 3,
            'fragment_retries': 3,
        }
        if "youtube.com" in url or "youtu.be" in url:
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
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки с ротацией: {e}", flush=True)
            return False
    return await asyncio.to_thread(_sync_rotating)

def get_available_qualities(url: str) -> list:
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        if "youtube.com" in url or "youtu.be" in url:
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
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return ["sd"]
            
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
