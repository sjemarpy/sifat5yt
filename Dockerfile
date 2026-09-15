FROM python:3.10-slim

# Java ও প্রয়োজনীয় টুলস ইনস্টল
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    zipalign \
    apksigner \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:10000", "app:app"]
