FROM python:3.11.9-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Бот не должен работать от root: создаём отдельного пользователя,
# которому доступна на запись только папка с временными файлами.
RUN useradd --system --no-create-home bot \
    && mkdir -p downloads \
    && chown bot:bot downloads
USER bot

CMD [ "python", "main.py" ]
