Python
import asyncio
import os
import yt_dlp

async def download_media(url: str, output_path: str) -> bool:
    """Выкачивает видео в максимальном качестве до 50MB"""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][filesize<50M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<50M]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 50 * 1024 * 1024, # 50 МБ
    }

    loop = asyncio.get_event_loop()
    try:
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        await loop.run_in_executor(None, _download)
        return os.path.exists(output_path)
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return False
