FROM python:3.11-slim

WORKDIR /app

# تثبيت متطلبات النظام التي يحتاجها Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src/bot.py"]
