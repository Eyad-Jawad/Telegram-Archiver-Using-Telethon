FROM python:3.14

WORKDIR /usr/src/telegramArchiver

COPY . .

RUN pip install --no-cache -r requirements.txt

ENTRYPOINT ["python", "./main.py"]