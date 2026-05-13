FROM python:3.11-slim

# Firefox/Camoufox dependencies + Xvfb for virtual display
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb xauth \
    libgtk-3-0 libx11-xcb1 libasound2 \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the Camoufox browser binary (Firefox-based anti-detect)
RUN python3 -m camoufox fetch

COPY . .
RUN mkdir -p data logs

ENV DISPLAY=:99
ENV PYTHONPATH=/app

CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & until [ -e /tmp/.X99-lock ]; do sleep 0.1; done; python fap-discord-bot/main.py"]
