ARG BUILD_FROM
FROM $BUILD_FROM

# Arbeitsverzeichnis
WORKDIR /app

# Installiere Python3, Pip und FFmpeg (Wichtig!)
RUN apk add --no-cache python3 py3-pip ffmpeg

# Installiere Python-Pakete
RUN pip3 install requests --break-system-packages

# Kopiere die Skripte ins Image
COPY run.sh /
COPY ftp_to_telegram.py /app/

# Mache das Start-Skript ausführbar
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]