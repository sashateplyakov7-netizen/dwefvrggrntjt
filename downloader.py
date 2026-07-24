# ==========================================
# 🎬 СКАЧИВАНИЕ С ОБРЕЗКОЙ ПО ВРЕМЕНИ
# ==========================================
def _sync_download_with_cut(url: str, output_path: str, start_time: str = None, end_time: str = None) -> bool:
    """
    Скачивает видео и обрезает по времени.
    start_time, end_time — в формате "MM:SS" или "HH:MM:SS"
    """
    try:
        print(f"🎬 Скачивание с обрезкой: {start_time} - {end_time}", flush=True)
        
        # Временный файл
        temp_path = output_path.replace('.mp4', '_temp.mp4')
        
        # Сначала скачиваем
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': temp_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'ignoreerrors': True,
            'user_agent': random.choice(USER_AGENTS),
        }
        
        # Добавляем куки для YouTube
        if "youtube.com" in url or "youtu.be" in url:
            cookies = get_youtube_cookies()
            if cookies:
                ydl_opts.update(cookies)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if not os.path.exists(temp_path):
            return False
        
        # 🔥 ОБРЕЗКА ЧЕРЕЗ FFMPEG
        import subprocess
        
        cmd = ['ffmpeg', '-i', temp_path]
        
        if start_time:
            cmd.extend(['-ss', start_time])
        if end_time:
            cmd.extend(['-to', end_time])
        
        cmd.extend(['-c', 'copy', '-avoid_negative_ts', '1', output_path])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Удаляем временный файл
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
    """Асинхронная загрузка с обрезкой по времени"""
    return await asyncio.to_thread(_sync_download_with_cut, url, output_path, start_time, end_time)
