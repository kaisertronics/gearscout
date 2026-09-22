FROM python:3.12-slim

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget curl ca-certificates gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libdbus-1-3 libxkbcommon0 libx11-6 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libpangocairo-1.0-0 libgtk-3-0 libglib2.0-0 \
    xvfb x11vnc fluxbox procps \
    novnc websockify \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's Chromium browser
RUN playwright install chromium

COPY . .

# Data volume — persists seen listings DB and FB session between runs
VOLUME ["/data"]

ENTRYPOINT ["python", "main.py"]
CMD ["schedule"]
