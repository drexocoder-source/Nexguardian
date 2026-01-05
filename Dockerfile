FROM python:3.10-slim-bookworm

WORKDIR /usr/src/app

COPY . .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

CMD ["python3", "bot.py"]
