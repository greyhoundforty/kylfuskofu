FROM python:3.12-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py ./app.py

# Copy the entrypoint script and make it executable
RUN chmod +x app.py

# Default command
ENTRYPOINT [ "./app.py" ]