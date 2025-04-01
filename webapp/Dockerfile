# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install UV
RUN pip install uv

# Copy requirements
COPY requirements.txt .

# Use UV to install dependencies into a virtual environment
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN uv venv /app/venv
RUN /app/venv/bin/uv pip install -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv

# Copy application code
COPY . .

# Set environment variables
ENV PATH="/app/venv/bin:$PATH"
ENV FLASK_APP=run.py
ENV DATABASE="/mnt/ext-bucket/catalog.db"

# Create non-root user
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run the application
EXPOSE 5000
CMD ["python", "run.py"]
