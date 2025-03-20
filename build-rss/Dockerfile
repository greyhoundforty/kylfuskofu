FROM python:3.12-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py ./cos_random_db.py

# Use Python to run the script instead of trying to execute it directly
ENTRYPOINT ["python", "app.py"]
