FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Fly.io sets PORT=8080; local runs default to 8000.
ENV PORT=8080

EXPOSE 8080

CMD ["python", "server.py"]
