#!/usr/bin/env python3
"""
Lädt Dateien von einem FTP-Server (Pfad: /YYYYMMDD/record/), konvertiert sie nach MP4
mit ffmpeg und sendet die MP4 per Telegram Bot an eine Gruppe.

Konfiguration über Umgebungsvariablen:
 - FTP_HOST, FTP_USER, FTP_PASS, FTP_PORT (optional)
 - BOT_TOKEN, CHAT_ID
 - TARGET_FPS (optional, 0 = automatisch)
 - DELETE_AFTER_SUCCESS (optional, '1'/true zum Löschen auf FTP)

Benötigt: `ffmpeg` im PATH und Python-Paket `requests`.
"""
import os
import ftplib
import tempfile
import subprocess
import shutil
import sys
import requests
import time
from datetime import datetime

ALLOWED_EXTS = ('.250', '.265')  # akzeptierte Quelldateiendungen
TARGET_FPS = None


def format_fps_value(fps):
    if fps is None:
        return '25'
    if abs(fps - round(fps)) < 1e-3:
        return str(int(round(fps)))
    return f"{fps:.3f}"


def get_env(name, required=True, default=None):
    val = os.environ.get(name, default)
    if required and (val is None or val == ''):
        print(f"Fehlende Umgebungsvariable: {name}")
        sys.exit(2)
    return val


def connect_ftp(host, user, passwd, port=None):
    if port:
        ftp = ftplib.FTP()
        ftp.connect(host, int(port))
    else:
        ftp = ftplib.FTP(host)
    ftp.login(user, passwd)
    return ftp


def list_day_directories(ftp):
    try:
        ftp.cwd('/')
        entries = ftp.nlst()
    except Exception as e:
        print(f"Fehler beim Auflisten der Root-Verzeichnisse: {e}")
        return []
    dirs = [entry for entry in entries if entry.isdigit()]
    dirs.sort()
    if dirs:
        print(f"Gefundene Tagesordner (chronologisch): {dirs}")
    else:
        print("Keine Tagesverzeichnisse gefunden.")
    return dirs


def list_files_in_record(ftp, day):
    path = f"/{day}/record/"
    print(f"Versuche, FTP-Verzeichnis zu wechseln: {path}")
    try:
        ftp.cwd(path)
    except Exception as e:
        print(f"Fehler beim Wechseln in Verzeichnis {path}: {e}")
        return []
    print(f"Überwache FTP-Verzeichnis: {path}")
    try:
        files = sorted(ftp.nlst())
    except Exception as e:
        print(f"Fehler beim Auflisten von Dateien in {path}: {e}")
        return []
    if files:
        print(f"Gefundene Dateien in {path}: {files}")
    else:
        print(f"Keine Dateien in {path}.")
    return files


def download_file(ftp, filename, dest_path):
    with open(dest_path, 'wb') as f:
        ftp.retrbinary(f'RETR {filename}', f.write)


def convert_250_to_mp4(src_path, dst_path):
    def probe_fps(path):
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=avg_frame_rate',
                '-of', 'default=nokey=1:noprint_wrappers=1', path
            ]
            p = subprocess.run(cmd, capture_output=True, text=True)
            out = p.stdout.strip()
            if not out:
                return None
            if '/' in out:
                num, den = out.split('/')
                try:
                    fps = float(num) / float(den) if float(den) != 0 else None
                except Exception:
                    fps = None
            else:
                try:
                    fps = float(out)
                except Exception:
                    fps = None
            return fps
        except Exception:
            return None

    print('Ermittle Frame-Rate via ffprobe (oder wende TARGET_FPS an)...')
    detected_fps = probe_fps(src_path)
    fps_source = 'automatisch'
    preferred_fps = None
    if TARGET_FPS and int(TARGET_FPS) > 0:
        preferred_fps = float(int(TARGET_FPS))
        fps_source = 'konfiguriert'
    elif detected_fps:
        preferred_fps = detected_fps
    else:
        preferred_fps = 25.0
    fps_str = format_fps_value(preferred_fps)
    print(f'Frame-Rate ({fps_source}): {fps_str} fps (detected: {detected_fps})')

    # ermittele, ob die Quelle eine Audiospur hat
    def probe_has_audio(path):
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'a',
                '-show_entries', 'stream=index', '-of', 'default=nokey=1:noprint_wrappers=1', path
            ]
            p = subprocess.run(cmd, capture_output=True, text=True)
            out = p.stdout.strip()
            return bool(out)
        except Exception:
            return False

    has_audio = probe_has_audio(src_path)
    print(f'Quelle hat Audiospur: {has_audio}')

    # Baue ffmpeg-Command: nur wenn es sich um reines Roh-HEVC ohne Audio handelt,
    # müssen wir das Input-Format (-f hevc) und die Input-Framerate setzen.
    cmd_recode = ['ffmpeg', '-y', '-fflags', '+genpts']
    lower = src_path.lower()
    if lower.endswith(('.265', '.h265', '.hevc')) and not has_audio:
        cmd_recode += ['-f', 'hevc', '-framerate', fps_str]
    # Input
    cmd_recode += ['-i', src_path]
    # Reencode: setze Ausgabe-framerate (-r) und fixe PTS/Avoid negative timestamps
    # Wenn Audio vorhanden ist, enkodiere zu AAC; sonst explizit ohne Audio (-an)
    cmd_recode += [
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-r', fps_str, '-filter:v', f'fps={fps_str}', '-fps_mode', 'cfr',
    ]
    if has_audio:
        cmd_recode += ['-c:a', 'aac', '-b:a', '128k']
    else:
        cmd_recode += ['-an']
    cmd_recode += ['-avoid_negative_ts', 'make_zero', '-movflags', '+faststart', dst_path]
    print(f'Führe ffmpeg (recode) aus: {cmd_recode}')
    # ausführliche Ausgabe, um Timing-Probleme sichtbar zu machen
    p2 = subprocess.run(cmd_recode, capture_output=True, text=True)
    print('ffmpeg stdout:', p2.stdout)
    print('ffmpeg stderr:', p2.stderr)
    if not (p2.returncode == 0 and os.path.exists(dst_path)):
        print(f'Konvertierung fehlgeschlagen (rc={p2.returncode})')
        return False, has_audio

    print('Neu-Kodierung erfolgreich — prüfe Dauer/Frames zur Validierung...')

    def probe_frame_count(path):
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                '-show_entries', 'stream=nb_read_frames', '-of', 'default=nokey=1:noprint_wrappers=1', path
            ]
            p = subprocess.run(cmd, capture_output=True, text=True)
            out = p.stdout.strip()
            if not out or out == 'N/A':
                return None
            return int(out)
        except Exception:
            return None

    def probe_duration(path):
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nokey=1:noprint_wrappers=1', path]
            p = subprocess.run(cmd, capture_output=True, text=True)
            out = p.stdout.strip()
            if not out:
                return None
            return float(out)
        except Exception:
            return None

    frames = probe_frame_count(src_path)
    out_duration = probe_duration(dst_path)
    print(f'Quell-Frames: {frames}, Ausgabe-Dauer: {out_duration}')

    fps_for_duration = preferred_fps if preferred_fps and preferred_fps > 0 else None
    if frames and out_duration and fps_for_duration:
        expected_dur = frames / float(fps_for_duration)
        if expected_dur > 0:
            multiplier = expected_dur / out_duration if out_duration > 0 else 1.0
            print(f'Erwartete Dauer: {expected_dur:.3f}s, tatsächliche Dauer: {out_duration:.3f}s, multiplier: {multiplier:.3f}')
            # Wenn Abweichung >5%, reencode mit setpts
            if abs(multiplier - 1.0) > 0.05:
                print('Große Abweichung erkannt, wende setpts-Reencode an...')
                tmp_fixed = dst_path + '.fixed.mp4'
                cmd_fix = [
                    'ffmpeg', '-y', '-i', dst_path,
                    '-filter:v', f'setpts=PTS*{multiplier}',
                    '-r', format_fps_value(fps_for_duration), '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', tmp_fixed
                ]
                print('Führe Fix-Command:', cmd_fix)
                pfix = subprocess.run(cmd_fix, capture_output=True, text=True)
                print('fix ffmpeg stdout:', pfix.stdout)
                print('fix ffmpeg stderr:', pfix.stderr)
                if pfix.returncode == 0 and os.path.exists(tmp_fixed):
                    # replace
                    try:
                        os.replace(tmp_fixed, dst_path)
                        print('Erfolgreich ersetzt durch fixierte Datei.')
                    except Exception as e:
                        print(f'Konnte fixierte Datei nicht ersetzen: {e}')
                else:
                    print('Fix-Reencode schlug fehl, behalte original Ausgabedatei.')
    else:
        print('Keine verlässlichen Frame- oder Duration-Informationen gefunden — überspringe Auto-Fix.')

    return True, has_audio


def send_file_telegram(bot_token, chat_id, file_path, caption=None):
    is_mp4 = str(file_path).lower().endswith('.mp4')
    if is_mp4:
        url = f'https://api.telegram.org/bot{bot_token}/sendVideo'
    else:
        url = f'https://api.telegram.org/bot{bot_token}/sendDocument'
    print(f'Sende an Telegram URL: {url}')
    try:
        fsize = os.path.getsize(file_path)
    except Exception:
        fsize = None
    print(f'Zu sendende Datei: {file_path} ({fsize} bytes)')
    try:
        with open(file_path, 'rb') as fp:
            if is_mp4:
                files = {'video': fp}
                data = {'chat_id': chat_id, 'supports_streaming': 'true'}
                if caption:
                    data['caption'] = caption
            else:
                files = {'document': fp}
                data = {'chat_id': chat_id}
                if caption:
                    data['caption'] = caption
            resp = requests.post(url, data=data, files=files, timeout=300)
    except Exception as e:
        print(f'Fehler beim Senden an Telegram: {e}')
        return False
    print(f'Telegram Antwort: {resp.status_code} {resp.reason}')
    print('Antwort-Body:', resp.text)
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f'Telegram API Fehler: {e} -- Antwort: {resp.text}')
        return False
    return True


def main():
    ftp_host = get_env('FTP_HOST')
    ftp_user = get_env('FTP_USER')
    ftp_pass = get_env('FTP_PASS')
    ftp_port = os.environ.get('FTP_PORT')
    bot_token = get_env('BOT_TOKEN')
    chat_id = get_env('CHAT_ID')
    target_fps_raw = os.environ.get('TARGET_FPS')
    global TARGET_FPS
    if target_fps_raw is not None and target_fps_raw != '':
        try:
            TARGET_FPS = int(target_fps_raw)
        except ValueError:
            print(f"Ungültiger TARGET_FPS-Wert: {target_fps_raw} -> automatische Ermittlung")
            TARGET_FPS = None
    delete_after = os.environ.get('DELETE_AFTER_SUCCESS', 'false').lower() in ('1', 'true', 'yes')

    processed = set()
    print('Starte Überwachungsloop (alle 60s). Drücke Strg+C zum Beenden.')
    try:
        while True:
            try:
                ftp = connect_ftp(ftp_host, ftp_user, ftp_pass, ftp_port)
            except Exception as e:
                print(f'FTP-Verbindung fehlgeschlagen: {e} -- neuer Versuch in 10s')
                time.sleep(10)
                continue

            day_dirs = list_day_directories(ftp)
            if not day_dirs:
                print('Keine Dateien im Record-Verzeichnis gefunden.')
                try:
                    ftp.quit()
                except Exception:
                    pass
                time.sleep(10)
                continue

            # Temporäres Arbeitsverzeichnis
            workdir = tempfile.mkdtemp(prefix='ftp_250_')

            try:
                for day in day_dirs:
                    files = list_files_in_record(ftp, day)
                    if not files:
                        continue
                    for fname in files:
                        if not any(fname.lower().endswith(ext) for ext in ALLOWED_EXTS):
                            continue
                        remote_key = f"{day}/record/{fname}"
                    if remote_key in processed:
                        continue
                    print(f'Bearbeite: {fname}')
                    # Debug: remote file size (wenn verfügbar)
                    try:
                        rsize = ftp.size(fname)
                        print(f'Remote dateigröße: {rsize} bytes')
                    except Exception:
                        print('Remote dateigröße: nicht verfügbar')
                    local_src = os.path.join(workdir, fname)
                    try:
                        download_file(ftp, fname, local_src)
                    except Exception as e:
                        print(f'Fehler beim Herunterladen {fname}: {e}')
                        continue

                    # Debug: lokaler Dateipfad und Größe
                    try:
                        lsize = os.path.getsize(local_src)
                        print(f'Heruntergeladen: {local_src} ({lsize} bytes)')
                    except Exception as e:
                        print(f'Konnte lokale Dateigröße nicht ermitteln: {e}')

                    base = os.path.splitext(fname)[0]
                    local_mp4 = os.path.join(workdir, base + '.mp4')
                    start = time.time()
                    ok, has_audio = convert_250_to_mp4(local_src, local_mp4)
                    dur = time.time() - start
                    print(f'Konvertierungsdauer: {dur:.1f}s')
                    if not ok:
                        print(f'Konvertierung von {fname} schlug fehl, überspringe Versand.')
                        continue

                    caption = '' #f'Aufnahme {base} vom {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                    print('Sende an Telegram...')
                    sent = send_file_telegram(bot_token, chat_id, local_mp4, caption)
                    if sent:
                        print(f'{local_mp4} erfolgreich gesendet.')
                        processed.add(remote_key)
                        if delete_after:
                            try:
                                ftp.delete(fname)
                                print(f'{fname} nach Erfolg auf FTP gelöscht.')
                            except Exception as e:
                                print(f'Warnung: Konnte {fname} nach Erfolg nicht löschen: {e}')
                    else:
                        print(f'Senden von {local_mp4} fehlgeschlagen.')

            finally:
                try:
                    ftp.quit()
                except Exception:
                    pass
                shutil.rmtree(workdir, ignore_errors=True)

            time.sleep(60)
    except KeyboardInterrupt:
        print('\nBeendet durch Benutzer')


if __name__ == '__main__':
    main()