FROM python:3.11-slim

WORKDIR /app

COPY movie_agent.py .

RUN pip install flask

EXPOSE 5001

CMD ["python", "movie_agent.py"]
