FROM python:3.11-slim
# Запусти в терминале Render или добавь в Dockerfile
playwright install chromium
# Установка ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем только requirements сначала (для кэширования)
COPY requirements.txt .

# Устанавливаем зависимости (кэшируется, пока requirements не изменился)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

# Порт для Render/Koyeb
EXPOSE 8080

# Запуск
CMD ["python", "bot.py"]
FROM python:3.11-slim

# Установка ffmpeg + Playwright dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Установка браузера для Playwright
RUN playwright install chromium

COPY . .

EXPOSE 8080
CMD ["python", "bot.py"]
