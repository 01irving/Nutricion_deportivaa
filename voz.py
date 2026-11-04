"""
Dictado por voz para la app (captura de datos hablados).

Graba desde el micrófono (sounddevice), detecta el final del enunciado por
silencio y reconoce el texto con el servicio de voz de Google a través de
SpeechRecognition (idioma es-MX). Requiere internet al momento de dictar.
"""
import threading
import time

try:
    import sounddevice as sd
except Exception:  # noqa: BLE001
    sd = None

try:
    import speech_recognition as sr
except Exception:  # noqa: BLE001
    sr = None

try:
    import audioop  # audioop-lts en Python 3.13
except Exception:  # noqa: BLE001
    audioop = None

FS = 16000           # frecuencia de muestreo (Hz)
BLOQUE = 0.1         # segundos por bloque de análisis
SILENCIO_STOP = 1.5  # segundos de silencio que cierran el dictado
MAX_SEG = 30         # duración máxima del dictado (segundos)
_ocupado = threading.Lock()


def disponible():
    """True si las librerías de voz están instaladas."""
    return sd is not None and sr is not None and audioop is not None


def dictar(al_terminar, parent=None, max_seg=MAX_SEG):
    """Graba un enunciado del micrófono y entrega el texto reconocido.

    al_terminar(texto, error) se ejecuta en el hilo de Tk (vía parent.after).
    Devuelve (ok, mensaje) para actualizar el botón de inmediato.
    """
    if not disponible():
        return False, "Faltan librerías de voz (SpeechRecognition/sounddevice)."
    if not _ocupado.acquire(blocking=False):
        return False, "Ya hay un dictado en curso."

    def trabajo():
        texto, error = "", ""
        try:
            bloques = []

            def _cb(indata, frames_, t_, estado):
                bloques.append(bytes(indata))

            with sd.InputStream(
                samplerate=FS, channels=1, dtype="int16",
                blocksize=int(FS * BLOQUE), callback=_cb,
            ):
                inicio = time.time()
                ruido = 0.0
                hablo = False
                silencio = 0.0
                while time.time() - inicio < max_seg:
                    time.sleep(BLOQUE)
                    if not bloques:
                        continue
                    rms = audioop.rms(bloques[-1], 2)
                    if not hablo:
                        # umbral adaptativo contra el ruido de fondo
                        ruido = 0.9 * ruido + 0.1 * rms if ruido else rms
                        if rms > max(500, ruido * 3):
                            hablo = True
                        continue
                    if rms < max(300, ruido * 2):
                        silencio += BLOQUE
                        if silencio >= SILENCIO_STOP:
                            break
                    else:
                        silencio = 0.0
            bruto = b"".join(bloques)
            if not hablo or len(bruto) < FS:
                error = (
                    "No se detectó voz. Acércate al micrófono "
                    "e intenta de nuevo."
                )
            else:
                reco = sr.Recognizer()
                audio = sr.AudioData(bruto, FS, 2)
                texto = reco.recognize_google(audio, language="es-MX")
        except sr.UnknownValueError:
            error = "No se entendió lo dicho. Intenta de nuevo más despacio."
        except sr.RequestError as e:  # noqa: BLE001
            error = f"Sin conexión al servicio de voz: {e}"
        except Exception as e:  # noqa: BLE001
            error = f"Error de micrófono: {e}"
        finally:
            _ocupado.release()
        if parent is not None:
            try:
                parent.after(0, lambda: al_terminar(texto, error))
                return
            except Exception:  # noqa: BLE001
                pass
        al_terminar(texto, error)

    threading.Thread(target=trabajo, daemon=True).start()
    return True, "🎙 Grabando... habla y haz una pausa al terminar"
