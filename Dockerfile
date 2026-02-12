FROM python:3.10-slim-bookworm

WORKDIR /usr/src/app

COPY . .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
