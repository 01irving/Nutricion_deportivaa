"""Contraseña de acceso a la app.

La contraseña se pide en una ventana modal al arrancar. Se guarda como
hash PBKDF2 (SHA-256) con sal aleatoria en la tabla configuracion de la
BD de cada instalación, así que cada equipo/profesional tiene la suya.
La primera vez la app pide crearla; después se puede cambiar desde el
diálogo PERSONALIZAR.

Cuando la ventana se muestra sin padre (arranque de la app), el diálogo
ES la ventana raíz: una Toplevel transient de un master oculto no se
vería en Windows.
"""
import hashlib
import secrets
import tkinter as tk
from tkinter import messagebox

import database

CLAVE_HASH = "acceso_hash"
CLAVE_SAL = "acceso_sal"
_ITERACIONES = 60000
_LARGO_MINIMO = 4

# Paleta igual a la de la ventana principal (acceso.py no importa
# nutricion_deportiva para evitar la importación circular).
NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"


# ------------------------------------------------------------------
# Hash y almacenamiento
# ------------------------------------------------------------------
def _hash(contrasena, sal_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), bytes.fromhex(sal_hex),
        _ITERACIONES,
    ).hex()


def hay_contrasena():
    return bool(database.get_config(CLAVE_HASH))


def verificar(contrasena):
    sal = database.get_config(CLAVE_SAL)
    guardado = database.get_config(CLAVE_HASH)
    if not sal or not guardado:
        return False
    return secrets.compare_digest(_hash(contrasena, sal), guardado)


def establecer(contrasena):
    sal = secrets.token_bytes(16)
    sal_hex = sal.hex()
    database.set_config(CLAVE_SAL, sal_hex)
    database.set_config(CLAVE_HASH, _hash(contrasena, sal_hex))


# ------------------------------------------------------------------
# Ventanas modales
# ------------------------------------------------------------------
def _ventana(parent, titulo):
    """Diálogo base: tk.Tk si no hay padre, Toplevel modal si lo hay.

    Devuelve (dialogo, marco). El cierre siempre es dialogo.destroy();
    cuando es raíz propia, mainloop() termina con destroy().
    """
    propio = parent is None
    if propio:
        dialogo = tk.Tk()
    else:
        dialogo = tk.Toplevel(parent)
        dialogo.transient(parent)
        dialogo.grab_set()
    dialogo.title(titulo)
    dialogo.configure(bg=GRIS_OSCURO)
    dialogo.resizable(False, False)
    try:
        dialogo.iconbitmap("icono_app.ico")
    except Exception:
        pass

    marco = tk.Frame(dialogo, bg=GRIS_OSCURO, padx=18, pady=16)
    marco.pack(fill="both", expand=True)
    dialogo._propio = propio
    return dialogo, marco


def _mostrar(dialogo, foco):
    """Centra, pone al frente y espera el cierre del diálogo."""
    dialogo.update_idletasks()
    ancho, alto = dialogo.winfo_width(), dialogo.winfo_height()
    x = max(0, (dialogo.winfo_screenwidth() - ancho) // 2)
    y = max(0, (dialogo.winfo_screenheight() - alto) // 2)
    dialogo.geometry(f"+{x}+{y}")
    dialogo.attributes("-topmost", True)
    dialogo.lift()
    dialogo.after(400, lambda: dialogo.attributes("-topmost", False))
    foco.focus_set()

    def salir():
        dialogo.destroy()
        if not dialogo._propio:
            # con raíz externa hay que soltar el grab manualmente al
            # destruir; con raíz propia no aplica
            pass

    dialogo.protocol("WM_DELETE_WINDOW", salir)

    if dialogo._propio:
        dialogo.mainloop()
    else:
        dialogo.wait_window(dialogo)


def _caja(parent, texto, mostrar="•", ancho=26):
    fila = tk.Frame(parent, bg=GRIS_OSCURO)
    fila.pack(fill="x", pady=(4, 0))
    tk.Label(
        fila, text=texto, width=16, anchor="e", fg=BLANCO,
        bg=GRIS_OSCURO, font=("Segoe UI", 9, "bold"),
    ).pack(side="left")
    entrada = tk.Entry(
        fila, width=ancho, bg=GRIS, fg=BLANCO, insertbackground=NEON,
        relief="flat", show=mostrar, justify="center",
        font=("Segoe UI", 10),
    )
    entrada.pack(side="left", padx=(6, 0), ipady=3)
    return entrada


def _botonera(parent, texto_principal, comando, texto_salir="SALIR"):
    barra = tk.Frame(parent, bg=GRIS_OSCURO)
    barra.pack(fill="x", pady=(10, 0))
    tk.Button(
        barra, text=texto_principal, command=comando, font=("Impact", 12),
        fg=NEGRO, bg=NEON, activebackground=NARANJA, activeforeground=BLANCO,
        relief="flat", padx=16, pady=5, cursor="hand2",
    ).pack(side="left", padx=(0, 8))
    tk.Button(
        barra, text=texto_salir, command=lambda: parent.destroy(),
        font=("Impact", 12), fg=NEON, bg=GRIS, activebackground=NARANJA,
        activeforeground=BLANCO, relief="flat", padx=16, pady=5, cursor="hand2",
    ).pack(side="left")


def dialogo_creacion(parent=None):
    """Pide crear la contraseña (primer arranque). True si quedó creada."""
    dialogo, marco = _ventana(parent, "Crear contraseña")

    tk.Label(
        marco, text="CREA TU CONTRASEÑA DE ACCESO", font=("Impact", 14),
        fg=NEON, bg=GRIS_OSCURO,
    ).pack(anchor="w", pady=(0, 10))

    campo = _caja(marco, "Nueva:")
    confirmacion = _caja(marco, "Repite:")

    mensaje = tk.Label(
        marco, text="", font=("Segoe UI", 8),
        fg=NARANJA, bg=GRIS_OSCURO, wraplength=300,
    )
    mensaje.pack(fill="x", pady=(6, 0))

    tk.Label(
        marco, text="Mínimo 4 caracteres. La necesitarás cada vez que "
        "abras la app.", font=("Segoe UI", 8), fg=GRIS_TEXTO,
        bg=GRIS_OSCURO, wraplength=300,
    ).pack(fill="x", pady=(0, 4))

    resultado = {"ok": False}

    def aceptar():
        nueva = campo.get()
        repite = confirmacion.get()
        if len(nueva) < _LARGO_MINIMO:
            mensaje.configure(text=f"Mínimo {_LARGO_MINIMO} caracteres.")
            return
        if nueva != repite:
            mensaje.configure(text="Las dos contraseñas no coinciden.")
            return
        establecer(nueva)
        resultado["ok"] = True
        dialogo.destroy()

    _botonera(marco, "GUARDAR", aceptar)

    dialogo.bind("<Return>", lambda _e: aceptar())
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    _mostrar(dialogo, campo)
    return resultado["ok"]


def dialogo_login(parent=None):
    """Pide la contraseña guardada. True si se verificó."""
    dialogo, marco = _ventana(parent, "Acceso")

    tk.Label(
        marco, text="CONTRASEÑA DE ACCESO", font=("Impact", 14),
        fg=NEON, bg=GRIS_OSCURO,
    ).pack(anchor="w", pady=(0, 10))

    campo = _caja(marco, "Contraseña:")

    mensaje = tk.Label(
        marco, text="", font=("Segoe UI", 8),
        fg=NARANJA, bg=GRIS_OSCURO, wraplength=300,
    )
    mensaje.pack(fill="x", pady=(6, 0))

    resultado = {"ok": False}

    def aceptar(_evento=None):
        if verificar(campo.get()):
            resultado["ok"] = True
            dialogo.destroy()
        else:
            mensaje.configure(text="Contraseña incorrecta.")
            campo.delete(0, "end")
            campo.focus_set()

    _botonera(marco, "ENTRAR", aceptar)

    dialogo.bind("<Return>", aceptar)
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    _mostrar(dialogo, campo)
    return resultado["ok"]


def pedir_acceso():
    """Puerta de entrada: crea la contraseña la 1a vez, luego la verifica."""
    if not hay_contrasena():
        return dialogo_creacion()
    return dialogo_login()


def dialogo_cambiar(parent=None):
    """Cambio de contraseña (desde PERSONALIZAR). True si se cambió."""
    dialogo, marco = _ventana(parent, "Cambiar contraseña")

    tk.Label(
        marco, text="CAMBIAR CONTRASEÑA DE ACCESO", font=("Impact", 14),
        fg=NEON, bg=GRIS_OSCURO,
    ).pack(anchor="w", pady=(0, 10))

    entrada_actual = _caja(marco, "Actual:")
    entrada_nueva = _caja(marco, "Nueva:")
    entrada_repite = _caja(marco, "Repite nueva:")

    mensaje = tk.Label(
        marco, text="", font=("Segoe UI", 8),
        fg=NARANJA, bg=GRIS_OSCURO, wraplength=300,
    )
    mensaje.pack(fill="x", pady=(6, 0))

    resultado = {"ok": False}

    def aceptar():
        nueva = entrada_nueva.get()
        if len(nueva) < _LARGO_MINIMO:
            mensaje.configure(text=f"Mínimo {_LARGO_MINIMO} caracteres.")
            return
        if nueva != entrada_repite.get():
            mensaje.configure(text="Las contraseñas nuevas no coinciden.")
            return
        if hay_contrasena() and not verificar(entrada_actual.get()):
            mensaje.configure(text="La contraseña actual no es correcta.")
            return
        establecer(nueva)
        resultado["ok"] = True
        if parent is not None:
            messagebox.showinfo(
                "Contraseña", "Contraseña actualizada.", parent=parent
            )
        dialogo.destroy()

    _botonera(marco, "GUARDAR", aceptar, texto_salir="CANCELAR")

    dialogo.bind("<Return>", lambda _e: aceptar())
    dialogo.bind("<Escape>", lambda _e: dialogo.destroy())
    _mostrar(dialogo, entrada_actual)
    return resultado["ok"]
