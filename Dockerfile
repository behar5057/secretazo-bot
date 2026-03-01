FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# هذه هي التغييرة المهمة - نسخ كل المحتوى بما في ذلك مجلد src
COPY . .

# التأكد من المسار الصحيح
CMD ["python", "-m", "src.bot"]
