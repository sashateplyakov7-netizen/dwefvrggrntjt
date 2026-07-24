FROM python:3.11-slim

# Установка ffmpeg + Playwright dependencies + aria2
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    aria2 \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Установка браузера для Playwright (уже есть в requirements.txt)
RUN playwright install chromium

# Копируем остальной код
COPY . .

# Порт для Render/Koyeb
EXPOSE 8080

# Запуск
CMD ["python", "bot.py"]
