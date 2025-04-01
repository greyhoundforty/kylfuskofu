# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install UV globally
RUN pip install uv

# Copy requirements
COPY requirements.txt .

# Use the global UV to create a virtual environment
RUN uv venv /app/venv

# Use the global UV command to install requirements into the venv
RUN uv pip install --python /app/venv/bin/python -r requirements.txt

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
