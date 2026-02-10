ARG BUILD_FROM
FROM $BUILD_FROM

# 1. Arbeitsverzeichnis
WORKDIR /app

# 2. Pakete installieren
RUN apk add --no-cache python3 py3-pip ffmpeg

# 3. Python-Libs
RUN pip3 install requests --break-system-packages

# 4. Dateien kopieren
COPY run.sh /
COPY ftp_to_telegram.py /app/

# 5. REPARATUR: Windows-Zeilenumbrüche entfernen (WICHTIG!)
# Dieser Befehl entfernt unsichtbare "\r" Zeichen aus den Dateien
RUN sed -i 's/\r$//' /run.sh && \
    sed -i 's/\r$//' /app/ftp_to_telegram.py

# 6. Ausführbar machen
RUN chmod a+x /run.sh

# 7. Starten
CMD [ "/run.sh" ]