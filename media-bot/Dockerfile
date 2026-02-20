FROM python:3.11-slim

WORKDIR /app

COPY agent_engine_pro.py .
COPY crawler_engine_pro_final.py .
COPY queue_engine.py .
COPY qbit_engine_daemon.py .
COPY runner.py .

RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4

CMD ["python", "-u", "runner.py"]