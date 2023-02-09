FROM alpine:3.12.3
ENV TZ=Europe/Moscow PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools
RUN mkdir -p /home/tg-bot/
ADD ./ /home/tg-bot/
RUN pip3 install -r /home/tg-bot/requirements.txt
RUN apk add  --no-cache ffmpeg
