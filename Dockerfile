FROM python:3.11-slim

# Chromium dependencies — libasound2t64 for Debian 12+
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libasound2t64 \
    libxshmfence1 libxss1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN patchright install chromium

COPY . .
RUN mkdir -p data logs

ENV DISPLAY=:99
ENV PYTHONPATH=/app

CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & until [ -e /tmp/.X99-lock ]; do sleep 0.1; done; python fap-discord-bot/main.py"]
