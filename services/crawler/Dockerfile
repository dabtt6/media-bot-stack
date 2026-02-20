FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests beautifulsoup4 flask

COPY crawler_engine_pro_final.py .
COPY queue_engine.py .
COPY agent_engine_pro.py .
COPY qbit_engine_daemon.py .
COPY main_pipeline.py .

CMD ["python3", "main_pipeline.py"]
