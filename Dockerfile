FROM python:3.12-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libnss3-tools \
    libxss1 \
    libxtst6 \
    fonts-noto-color-emoji \
    fonts-freefont-ttf \
    xvfb \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN playwright install

COPY cos_random_db.py ./cos_random_db.py

# Copy the entrypoint script and make it executable
RUN chmod +x cos_random_db.py

# Default command
ENTRYPOINT [ "./cos_random_db.py" ]