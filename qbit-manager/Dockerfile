FROM python:3.11-slim

WORKDIR /app
COPY manager.py .

RUN pip install requests

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "manager.py"]
