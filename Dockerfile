FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

WORKDIR /app
RUN git clone