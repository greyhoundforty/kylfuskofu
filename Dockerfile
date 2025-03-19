FROM python:3.12-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN playwright install

COPY cos_random_db.py ./cos_random_db.py

# Copy the entrypoint script and make it executable
RUN chmod +x cos_random_db.py

# Default command
ENTRYPOINT [ "./cos_random_db.py" ]