FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4

ENV PYTHONUNBUFFERED=1

CMD ["python", "runner.py"]