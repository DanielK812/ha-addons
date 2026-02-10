ARG BUILD_FROM
FROM $BUILD_FROM

# 1. Arbeitsverzeichnis
WORKDIR /app

# 2. Pakete installieren (ffmpeg ist wichtig!)
RUN apk add --no-cache python3 py3-pip ffmpeg

# 3. Python-Libs installieren
RUN pip3 install requests --break-system-packages

# 4. Skripte kopieren
# WICHTIG: Kopiere das run.sh Script.
# Kopiere KEINE bashio.sh oder andere Systemdateien, das macht das Base-Image kaputt!
COPY run.sh /
COPY ftp_to_telegram.py /app/

# 5. Rechte vergeben
RUN chmod a+x /run.sh

# 6. Der Startbefehl (WICHTIG!)
# Nutze CMD, niemals ENTRYPOINT.
# Nutze eckige Klammern ["..."], sonst startet eine Shell dazwischen und klaut PID 1.
CMD [ "/run.sh" ]