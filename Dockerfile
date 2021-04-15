FROM alpine as intermediate
LABEL stage=intermediate

WORKDIR /temp
RUN apk update && \
    apk add --update git && \
    apk add --update openssh
RUN git clone https://github.com/Crunchy-Bot/web-back.git

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim
WORKDIR /app
COPY --from=intermediate /temp/web-back /app

RUN pip install -r requirements.txt