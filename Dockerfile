FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create supervisor configuration
RUN echo "[supervisord]\nnodaemon=true\n\n[program:bot]\ncommand=python main.py\n\n[program:healthcheck]\ncommand=python healthcheck.py" > /etc/supervisor/conf.d/supervisord.conf

# Expose port for healthcheck
EXPOSE 8080

# Start supervisor
CMD ["/usr/bin/supervisord"] 