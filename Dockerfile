FROM python:3.11-slim

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
