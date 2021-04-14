FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

WORKDIR /temp
RUN git clone https://github.com/Crunchy-Bot/web-back.git

WORKDIR /app
RUN cp /temp/web-back /app

RUN pip install -r requirements.txt