ARG BUILD_FROM
FROM $BUILD_FROM

# 1. Arbeitsverzeichnis
WORKDIR /app

# 2. Pakete installieren (ffmpeg ist wichtig!)
RUN apk add --no-cache python3 py3-pip ffmpeg

# 3. Python-Bibliotheken installieren
RUN pip3 install requests --break-system-packages

# 4. Dateien kopieren
COPY run.sh /
COPY ftp_to_telegram.py /app/

# 5. REPARATUR-BEFEHL (Entfernt Windows-Zeilenumbrüche)
# Das ist der entscheidende Teil, der den Absturz verhindert:
RUN sed -i 's/\r$//' /run.sh && \
    sed -i 's/\r$//' /app/ftp_to_telegram.py

# 6. Ausführbar machen
RUN chmod a+x /run.sh

# 7. Startbefehl
CMD [ "/run.sh" ]