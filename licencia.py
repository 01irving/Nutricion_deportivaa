"""Licencia de activación por equipo.

Cada computadora genera un CÓDIGO DE INSTALACIÓN derivado del
MachineGuid de Windows. El autor del programa (y solo él, con el script
privado generar_licencia.py) convierte ese código en una CLAVE DE
ACTIVACIÓN. Al activarse, la clave se guarda en la BD junto con la
huella del equipo: copiar la BD a otra computadora NO transfiere la
licencia, ahí vuelve a pedir activación.

Nota honesta: al ser Python empacado, un usuario muy técnico podría
extraer la lógica de verificación. Esto disuade el uso casual, no es
DRM infalible.
"""
import hashlib
import hmac
import os
import secrets
import tkinter as tk
import uuid
from datetime import datetime, timedelta
from tkinter import messagebox

import database

# Secreto compartido entre la app y generar_licencia.py.
_SECRETO = b"ND::licencia::v1::qW7tR2mZ9xK4pL8sJ5vB3nC6"

CLAVE_LICENCIA = "licencia_clave"
CLAVE_HUELLA = "licencia_huella"
CLAVE_PRUEBA = "prueba_inicio"

DIAS_PRUEBA = 30

# Paleta local (evita importar nutricion_deportiva).
NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"


# ------------------------------------------------------------------
# Identidad del equipo y claves
# ------------------------------------------------------------------
def _guid_maquina():
    """MachineGuid de Windows; alternativa si el registro no está."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography"
        ) as clave:
            valor, _ = winreg.QueryValueEx(clave, "MachineGuid")
        return str(valor)
    except Exception:
        return f"alt-{uuid.getnode():012x}"


def _huella():
    """Huella del equipo para amarrar la activación guardada."""
    return hashlib.sha256(
        _SECRETO + _guid_maquina().encode("utf-8")
    ).hexdigest()


def _normalizar(texto):
    return "".join(c for c in str(texto).upper() if c.isalnum())


def _agrupar(texto, n):
    return "-".join(texto[i:i + n] for i in range(0, len(texto), n))


def codigo_instalacion():
    """XXXX-XXXX-XXXX-XXXX único por computadora, para mandar al autor."""
    h = hmac.new(
        _SECRETO, _guid_maquina().encode("utf-8"), hashlib.sha256
    ).hexdigest().upper()[:16]
    return _agrupar(h, 4)


def clave_para(codigo):
    """Clave de activación para un código (solo la usa generar_licencia)."""
    limpio = _normalizar(codigo)
    h = hmac.new(
        _SECRETO, b"K" + limpio.encode("ascii"), hashlib.sha256
    ).hexdigest().upper()[:20]
    return _agrupar(h, 5)


# ------------------------------------------------------------------
# Estado de activación
# ------------------------------------------------------------------
def activada():
    guardada = _normalizar(database.get_config(CLAVE_LICENCIA))
    if not guardada:
        return False
    if database.get_config(CLAVE_HUELLA) != _huella():
        return False  # la BD se copió de otro equipo: reactivar
    esperada = _normalizar(clave_para(codigo_instalacion()))
    return secrets.compare_digest(guardada, esperada)


def activar(clave):
    """True si la clave corresponde a este equipo; guarda la activación."""
    limpio = _normalizar(clave)
    esperada = _normalizar(clave_para(codigo_instalacion()))
    if limpio and secrets.compare_digest(limpio, esperada):
        database.set_config(CLAVE_LICENCIA, limpio)
        database.set_config(CLAVE_HUELLA, _huella())
        return True
    return False


# ------------------------------------------------------------------
# Período de prueba (30 días desde el primer arranque, sin licencia)
# ------------------------------------------------------------------
def _ruta_marcador():
    """Marcador fuera de la BD: sobrevive a borrar el programa o la BD."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    carpeta = os.path.join(base, "NutricionDeportiva")
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, "prueba.ini")


def _inicio_prueba():
    """Fecha de inicio más antigua entre la BD y el marcador local."""
    candidatos = []
    texto_bd = database.get_config(CLAVE_PRUEBA)
    if texto_bd:
        try:
            candidatos.append(
                datetime.strptime(texto_bd, "%Y-%m-%d %H:%M")
            )
        except ValueError:
            pass
    try:
        with open(_ruta_marcador(), "r", encoding="utf-8") as f:
            texto = f.read().strip()
        if texto:
            candidatos.append(datetime.strptime(texto, "%Y-%m-%d %H:%M"))
    except (OSError, ValueError):
        pass
    return min(candidatos) if candidatos else None


def iniciar_prueba():
    """Fija el inicio del período de prueba (se llama en el 1er arranque)."""
    texto = datetime.now().strftime("%Y-%m-%d %H:%M")
    database.set_config(CLAVE_PRUEBA, texto)
    try:
        with open(_ruta_marcador(), "w", encoding="utf-8") as f:
            f.write(texto)
    except OSError:
        pass


def dias_restantes_prueba():
    inicio = _inicio_prueba()
    if inicio is None:
        return DIAS_PRUEBA
    transcurridos = (datetime.now() - inicio).days
    return max(0, DIAS_PRUEBA - transcurridos)


def en_prueba():
    """Período de prueba vigente (sin licencia y con días restantes)."""
    return not activada() and dias_restantes_prueba() > 0


# ------------------------------------------------------------------
# Diálogo de activación
# ------------------------------------------------------------------
def pedir_activacion(parent=None):
    """Puerta de licencia.

    Con licencia válida abre directo. Sin licencia corre la prueba de
    30 días (avisando los días restantes) y al vencer solo continúa
    activando con la clave.
    """
    if activada():
        return True

    if _inicio_prueba() is None:
        iniciar_prueba()
    restantes = dias_restantes_prueba()

    # Sin padre, el diálogo ES la raíz: una Toplevel transient de un
    # master oculto no llega a verse en Windows.
    propio = parent is None
    if propio:
        dialogo = tk.Tk()
    else:
        dialogo = tk.Toplevel(parent)
        dialogo.transient(parent)
        dialogo.grab_set()
    dialogo.title("Activación")
    dialogo.configure(bg=GRIS_OSCURO)
    dialogo.resizable(False, False)
    try:
        dialogo.iconbitmap("icono_app.ico")
    except Exception:
        pass
    dialogo._propio = propio

    marco = tk.Frame(dialogo, bg=GRIS_OSCURO, padx=18, pady=16)
    marco.pack(fill="both", expand=True)

    tk.Label(
        marco, text="ACTIVACIÓN DEL PROGRAMA", font=("Impact", 14),
        fg=NEON, bg=GRIS_OSCURO,
    ).pack(anchor="w", pady=(0, 6))

    # Estado del período de prueba
    if restantes > 0:
        inicio = _inicio_prueba()
        vence = (inicio + timedelta(days=DIAS_PRUEBA)).strftime("%d/%m/%Y")
        estado = tk.Label(
            marco,
            text=f"VERSÍON DE PRUEBA — todas las funciones · te quedan "
                 f"{restantes} día(s) · vence el {vence}",
            font=("Segoe UI", 9, "bold"), fg=AMARILLO, bg=GRIS_OSCURO,
            wraplength=380, justify="left",
        )
        estado.pack(anchor="w", pady=(0, 6))
    else:
        estado = tk.Label(
            marco,
            text="EL PERÍODO DE PRUEBA TERMINÓ. Activa el programa para "
                 "seguir usándolo.",
            font=("Segoe UI", 10, "bold"), fg=ROJO, bg=GRIS_OSCURO,
            wraplength=380, justify="left",
        )
        estado.pack(anchor="w", pady=(0, 6))

    tk.Label(
        marco,
        text="Envía tu CÓDIGO DE INSTALACIÓN para recibir tu clave de "
             "activación (una sola vez por computadora).",
        font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        wraplength=380, justify="left",
    ).pack(anchor="w", pady=(0, 8))

    codigo = codigo_instalacion()
    fila_codigo = tk.Frame(marco, bg=GRIS_OSCURO)
    fila_codigo.pack(fill="x", pady=(0, 4))
    tk.Label(
        fila_codigo, text="CÓDIGO DE INSTALACIÓN:", font=("Segoe UI", 9, "bold"),
        fg=BLANCO, bg=GRIS_OSCURO,
    ).pack(side="left")
    tk.Label(
        fila_codigo, text=codigo, font=("Consolas", 12, "bold"),
        fg=NARANJA, bg=GRIS_OSCURO,
    ).pack(side="left", padx=8)

    def copiar():
        dialogo.clipboard_clear()
        dialogo.clipboard_append(codigo)
        aviso.configure(text="Código copiado al portapapeles.")

    tk.Button(
        marco, text="COPIAR CÓDIGO", command=copiar,
        font=("Segoe UI", 9, "bold"), fg=NEON, bg=GRIS,
        activebackground=NARANJA, activeforeground=BLANCO,
        relief="flat", padx=12, pady=3, cursor="hand2",
    ).pack(anchor="w")

    fila_clave = tk.Frame(marco, bg=GRIS_OSCURO)
    fila_clave.pack(fill="x", pady=(12, 0))
    tk.Label(
        fila_clave, text="CLAVE DE ACTIVACIÓN:", font=("Segoe UI", 9, "bold"),
        fg=BLANCO, bg=GRIS_OSCURO,
    ).pack(side="left")
    entrada = tk.Entry(
        fila_clave, width=28, bg=GRIS, fg=BLANCO, insertbackground=NEON,
        relief="flat", justify="center", font=("Consolas", 11),
    )
    entrada.pack(side="left", padx=(8, 0), ipady=3)

    aviso = tk.Label(
        marco, text="", font=("Segoe UI", 8), fg=NARANJA, bg=GRIS_OSCURO,
        wraplength=380,
    )
    aviso.pack(fill="x", pady=(4, 0))

    resultado = {"ok": False, "continuar": False}

    def continuar():
        if dias_restantes_prueba() > 0:
            resultado["continuar"] = True
            dialogo.destroy()

    def aceptar(_evento=None):
        if activar(entrada.get()):
            resultado["ok"] = True
            dialogo.destroy()
        else:
            aviso.configure(text="Clave incorrecta para este código.")

    barra = tk.Frame(marco, bg=GRIS_OSCURO)
    barra.pack(fill="x", pady=(10, 0))
    if restantes > 0:
        tk.Button(
            barra, text="CONTINUAR CON LA PRUEBA", command=continuar,
            font=("Impact", 12), fg=NEGRO, bg=NARANJA,
            activebackground=NEON, activeforeground=NEGRO,
            relief="flat", padx=12, pady=5, cursor="hand2",
        ).pack(side="left", padx=(0, 8))
    tk.Button(
        barra, text="ACTIVAR", command=aceptar, font=("Impact", 12),
        fg=NEGRO, bg=NEON, activebackground=NARANJA, activeforeground=BLANCO,
        relief="flat", padx=16, pady=5, cursor="hand2",
    ).pack(side="left", padx=(0, 8))
    tk.Button(
        barra, text="SALIR", command=dialogo.destroy,
        font=("Impact", 12), fg=NEON, bg=GRIS, activebackground=NARANJA,
        activeforeground=BLANCO, relief="flat", padx=16, pady=5, cursor="hand2",
    ).pack(side="left")

    dialogo.bind("<Return>", aceptar)
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)

    dialogo.update_idletasks()
    ancho, alto = dialogo.winfo_width(), dialogo.winfo_height()
    x = max(0, (dialogo.winfo_screenwidth() - ancho) // 2)
    y = max(0, (dialogo.winfo_screenheight() - alto) // 2)
    dialogo.geometry(f"+{x}+{y}")
    dialogo.attributes("-topmost", True)
    dialogo.lift()
    dialogo.after(400, lambda: dialogo.attributes("-topmost", False))
    if restantes > 0:
        entrada.focus_set()
    else:
        entrada.focus_set()

    if dialogo._propio:
        dialogo.mainloop()
    else:
        dialogo.wait_window(dialogo)
    return resultado["ok"] or resultado["continuar"]
