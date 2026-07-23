import asyncio
import os
import yt_dlp

def _sync_download(url: str, output_path: str) -> bool:
    ydl_opts = {
        # Сначала ищет готовый mp4 со звуком до 50MB (без склейки), если нет — берет лучшее комбинированное
        'format': 'b[ext=mp4][filesize<50M]/best[ext=mp4][filesize<50M]/best[filesize<50M]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'max_filesize': 50 * 1024 * 1024,  # Лимит 50 МБ
        'concurrent_fragment_downloads': 5, # Скачивание в 5 потоков
        'socket_timeout': 10,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.exists(output_path)
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}", flush=True)
        return False

async def download_media(url: str, output_path: str) -> bool:
    # Выносим синхронный вызов yt-dlp в отдельный поток, чтобы не вешать asyncio-петлю бота
    return await asyncio.to_thread(_sync_download, url, output_path)
