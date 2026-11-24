FROM python:3.13-slim AS web
WORKDIR /app
RUN pip install --no-cache-dir Flask==3.1.3 gunicorn==23.0.0
CMD ["gunicorn","--bind","0.0.0.0:8000","--threads","4","app:app"]

FROM web AS archive
COPY archives-site/ .

FROM web AS game
RUN apt-get update && apt-get install -y --no-install-recommends e2fsprogs && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir Pillow==12.2.0
COPY files/*.py files/
COPY game/ .
COPY story/ story/
COPY archives-site/static/raghavan.jpg static/reading-room.jpg
