FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies + Xvfb for virtual display
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libx11-xcb1 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Patchright/Playwright browsers
RUN python -m patchright install --with-deps chromium

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data logs

# Set Python path
ENV PYTHONPATH=/app

# Run the bot inside Xvfb virtual display (Chromium needs a display)
ENV DISPLAY=:99
CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & sleep 1 && exec python fap-discord-bot/main.py"]
