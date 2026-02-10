FROM ghcr.io/home-assistant/amd64-base-python:3.13.4

WORKDIR /app

COPY kamera/ftp_to_telegram.py ./

RUN pip install --no-cache-dir requests

COPY bashio.sh /usr/bin/bashio
RUN chmod +x /usr/bin/bashio

CMD ["python", "./ftp_to_telegram.py"]
