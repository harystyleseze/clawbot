FROM python:3.12-slim

WORKDIR /app

# Install deps first (better Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create data directory
RUN mkdir -p data

# Seed database on first run, then start bot
CMD ["sh", "-c", "python -m src.db.seed && python -m src"]
