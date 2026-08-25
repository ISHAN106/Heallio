FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system packages required by Pillow (image support) and build tools
RUN apt-get update && \
	apt-get install -y --no-install-recommends build-essential libjpeg-dev zlib1g-dev && \
	rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install requirements and ensure Pillow is available
RUN pip install --no-cache-dir -r requirements.txt Pillow==9.5.0

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
