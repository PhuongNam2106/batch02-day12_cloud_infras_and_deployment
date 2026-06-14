FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY 05-scaling-reliability/production/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 05-scaling-reliability/production/app.py .
COPY 05-scaling-reliability/production/utils ./utils

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
