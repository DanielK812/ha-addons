ARG BUILD_FROM
FROM $BUILD_FROM

# 1. Arbeitsverzeichnis setzen
WORKDIR /app

# 2. Notwendige Pakete installieren (FFmpeg fehlt bei dir!)
# Python ist im Base-Image schon drin, aber pip und ffmpeg müssen oft dazu.
RUN apk add --no-cache ffmpeg py3-pip

# 3. Python-Bibliotheken installieren
# --break-system-packages ist bei neueren Python-Versionen in Alpine nötig
RUN pip3 install requests --break-system-packages

# 4. Dateien kopieren
# WICHTIG: Kopiere run.sh, das ist die Brücke zwischen Home Assistant und Python!
COPY run.sh /
COPY ftp_to_telegram/ftp_to_telegram.py /app/

# 5. Ausführbar machen
RUN chmod a+x /run.sh

# 6. Start-Befehl
# Nicht direkt Python starten, sondern das run.sh Script,
# damit die Umgebungsvariablen (Config) geladen werden.
CMD [ "/run.sh" ]