"""Gestor de licencias — USO PRIVADO DEL AUTOR.

Control de QUIÉN tiene el software de Nutrición Deportiva y QUÉ versión
se le entregó. Registra cada licencia (profesional, código de
instalación, clave generada, contacto) y cada entrega/actualización con
su fecha y versión; marca en rojo a quien no tiene la versión vigente.

BD propia: licencias_entregadas.db (junto a este archivo). No se
empaqueta en la app ni viaja en los zips de distribución.

Uso:
    python gestor_licencias.py
"""
import os
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import licencia
from version import VERSION

RUTA_BD = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "licencias_entregadas.db"
)

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"
AMARILLO = "#FFD600"
VERDE = "#00E676"
ROJO = "#FF1744"


# ------------------------------------------------------------------
# BD
# ------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(RUTA_BD)
    conn.row_factory = sqlite3.Row
    return conn


def init_bd():
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS licencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profesional TEXT NOT NULL,
                contacto TEXT DEFAULT '',
                codigo TEXT NOT NULL,
                clave TEXT NOT NULL,
                fecha TEXT NOT NULL,
                notas TEXT DEFAULT ''
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS entregas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                licencia_id INTEGER NOT NULL REFERENCES licencias(id)
                    ON DELETE CASCADE,
                fecha TEXT NOT NULL,
                version TEXT NOT NULL,
                notas TEXT DEFAULT ''
            )"""
        )


def registrar_licencia(profesional, contacto, codigo, notas=""):
    """Da de alta una licencia con su clave y la entrega inicial.

    Si el código ya estaba registrado, actualiza datos y devuelve su id.
    """
    codigo = licencia._normalizar(codigo)
    clave = licencia.clave_para(codigo)
    hoy = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        fila = conn.execute(
            "SELECT id FROM licencias WHERE codigo = ?", (codigo,)
        ).fetchone()
        if fila:
            lic_id = fila["id"]
            conn.execute(
                """UPDATE licencias SET profesional = ?, contacto = ?,
                   clave = ?, notas = ? WHERE id = ?""",
                (profesional.strip(), contacto.strip(), clave,
                 notas.strip(), lic_id),
            )
        else:
            cur = conn.execute(
                """INSERT INTO licencias
                   (profesional, contacto, codigo, clave, fecha, notas)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (profesional.strip(), contacto.strip(), codigo, clave,
                 hoy, notas.strip()),
            )
            lic_id = cur.lastrowid
        # registrar la entrega inicial / re-entrega si no hay ninguna
        # de la versión vigente
        ya = conn.execute(
            """SELECT 1 FROM entregas WHERE licencia_id = ? AND version = ?""",
            (lic_id, VERSION),
        ).fetchone()
        if not ya:
            conn.execute(
                """INSERT INTO entregas (licencia_id, fecha, version, notas)
                   VALUES (?, ?, ?, ?)""",
                (lic_id, hoy, VERSION, "Entrega inicial"),
            )
    return lic_id


def listar_licencias(busqueda=""):
    patron = f"%{busqueda.strip()}%"
    with get_conn() as conn:
        filas = conn.execute(
            """SELECT l.*,
                      (SELECT version FROM entregas e
                       WHERE e.licencia_id = l.id
                       ORDER BY e.fecha DESC, e.id DESC LIMIT 1)
                       AS version_entregada,
                      (SELECT fecha FROM entregas e
                       WHERE e.licencia_id = l.id
                       ORDER BY e.fecha DESC, e.id DESC LIMIT 1)
                       AS ultima_entrega
               FROM licencias l
               WHERE l.profesional LIKE ? OR l.contacto LIKE ? OR l.codigo LIKE ?
               ORDER BY l.profesional COLLATE NOCASE""",
            (patron, patron, patron),
        ).fetchall()
    return [dict(f) for f in filas]


def obtener_licencia(lic_id):
    with get_conn() as conn:
        fila = conn.execute(
            "SELECT * FROM licencias WHERE id = ?", (lic_id,)
        ).fetchone()
    return dict(fila) if fila else None


def entregas_de(lic_id):
    with get_conn() as conn:
        filas = conn.execute(
            """SELECT * FROM entregas WHERE licencia_id = ?
               ORDER BY fecha DESC, id DESC""",
            (lic_id,),
        ).fetchall()
    return [dict(f) for f in filas]


def registrar_entrega(lic_id, version, notas=""):
    hoy = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO entregas (licencia_id, fecha, version, notas)
               VALUES (?, ?, ?, ?)""",
            (lic_id, hoy, version.strip(), notas.strip()),
        )


def eliminar_licencia(lic_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM licencias WHERE id = ?", (lic_id,))


# ------------------------------------------------------------------
# GUI
# ------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Gestor de licencias — Nutrición Deportiva v{VERSION}")
        self.configure(bg=NEGRO)
        self.geometry("980x600")
        self.minsize(860, 480)
        try:
            self.iconbitmap("icono_app.ico")
        except Exception:
            pass
        init_bd()
        self._estilos()

        # encabezado
        barra = tk.Frame(self, bg=NEGRO)
        barra.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(
            barra, text="GESTOR DE LICENCIAS", font=("Impact", 18),
            fg=NEON, bg=NEGRO,
        ).pack(side="left")
        tk.Label(
            barra, text=f"Versión vigente: v{VERSION}",
            font=("Segoe UI", 10, "bold"), fg=NARANJA, bg=NEGRO,
        ).pack(side="left", padx=16)
        tk.Button(
            barra, text="+ NUEVA LICENCIA", command=self._nueva_licencia,
            font=("Impact", 11), fg=NEGRO, bg=NARANJA,
            activebackground=NEON, activeforeground=NEGRO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(side="right")

        barra_busq = tk.Frame(self, bg=NEGRO)
        barra_busq.pack(fill="x", padx=10, pady=(0, 6))
        tk.Label(barra_busq, text="Buscar:", font=("Segoe UI", 10, "bold"),
                 fg=BLANCO, bg=NEGRO).pack(side="left")
        self.var_busqueda = tk.StringVar()
        self.var_busqueda.trace_add("write", lambda *_: self._refrescar())
        tk.Entry(barra_busq, width=34, bg=GRIS, fg=BLANCO,
                 insertbackground=NEON, relief="flat",
                 textvariable=self.var_busqueda).pack(
            side="left", padx=8, ipady=3)

        # lista
        columnas = ("profesional", "contacto", "version", "entrega", "estado")
        self.tree = ttk.Treeview(self, columns=columnas, show="headings",
                                 style="Lic.Treeview", height=9)
        for col, texto, ancho in (
            ("profesional", "Profesional", 200),
            ("contacto", "Contacto", 140),
            ("version", "Versión", 70),
            ("entrega", "Última entrega", 95),
            ("estado", "Estado", 120),
        ):
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=ancho, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.tag_configure("aldia", foreground=VERDE)
        self.tree.tag_configure("viejo", foreground=ROJO)
        self.tree.bind("<<TreeviewSelect>>", self._al_seleccionar)

        # detalle: entregas del seleccionado
        detalle = tk.LabelFrame(self, bg=GRIS_OSCURO, fg=NEON,
                                text=" Entregas del profesional ",
                                font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        detalle.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self.lbl_sel = tk.Label(detalle, text="—", font=("Segoe UI", 10, "bold"),
                                fg=BLANCO, bg=GRIS_OSCURO)
        self.lbl_sel.pack(anchor="w", pady=(0, 4))

        self.tree_entregas = ttk.Treeview(
            detalle, columns=("fecha", "version", "notas"), show="headings",
            style="Lic.Treeview", height=5,
        )
        for col, texto, ancho in (
            ("fecha", "Fecha", 85), ("version", "Versión", 70),
            ("notas", "Notas", 480),
        ):
            self.tree_entregas.heading(col, text=texto)
            self.tree_entregas.column(col, width=ancho, anchor="w")
        self.tree_entregas.pack(fill="both", expand=True)

        barra_acc = tk.Frame(detalle, bg=GRIS_OSCURO)
        barra_acc.pack(fill="x", pady=(6, 0))
        tk.Button(
            barra_acc, text="REGISTRAR ACTUALIZACIÓN",
            command=self._registrar_entrega,
            font=("Impact", 11), fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side="left", padx=(0, 6))
        tk.Button(
            barra_acc, text="COPIAR CLAVE", command=self._copiar_clave,
            font=("Segoe UI", 9, "bold"), fg=NEON, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=10, pady=4, cursor="hand2",
        ).pack(side="left", padx=(0, 6))
        tk.Button(
            barra_acc, text="ELIMINAR", command=self._eliminar,
            font=("Segoe UI", 9, "bold"), fg=NEGRO, bg=ROJO,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=10, pady=4, cursor="hand2",
        ).pack(side="left")

        self._refrescar()

    def _estilos(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("Lic.Treeview", background=GRIS_OSCURO,
                         fieldbackground=GRIS_OSCURO, foreground=BLANCO,
                         rowheight=24, borderwidth=0)
        estilo.configure("Lic.Treeview.Heading", background=GRIS,
                         foreground=NEON, font=("Segoe UI", 9, "bold"))
        estilo.map("Lic.Treeview", background=[("selected", NARANJA)])

    # ------------------------------------------------------------------
    def _refrescar(self):
        sel = self.tree.selection()
        iid_sel = sel[0] if sel else None
        for item in self.tree.get_children():
            self.tree.delete(item)
        for l in listar_licencias(self.var_busqueda.get()):
            al_dia = l["version_entregada"] == VERSION
            self.tree.insert(
                "", tk.END, iid=str(l["id"]),
                values=(l["profesional"], l["contacto"],
                        l["version_entregada"] or "—",
                        l["ultima_entrega"] or "—",
                        "AL DÍA" if al_dia else "DESACTUALIZADO"),
                tags=("aldia",) if al_dia else ("viejo",),
            )
        if iid_sel and self.tree.exists(iid_sel):
            self.tree.selection_set(iid_sel)

    def _id_seleccionado(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _al_seleccionar(self, _evento=None):
        lic_id = self._id_seleccionado()
        if not lic_id:
            return
        l = obtener_licencia(lic_id)
        if not l:
            return
        self.lbl_sel.configure(
            text=f"{l['profesional']}  ·  {l['contacto'] or 'sin contacto'}  "
                 f"·  código {l['codigo']}"
        )
        for item in self.tree_entregas.get_children():
            self.tree_entregas.delete(item)
        for e in entregas_de(lic_id):
            self.tree_entregas.insert(
                "", tk.END,
                values=(e["fecha"], e["version"], e["notas"]),
            )

    # ------------------------------------------------------------------
    def _nueva_licencia(self):
        dialogo = tk.Toplevel(self)
        dialogo.title("Nueva licencia")
        dialogo.configure(bg=GRIS_OSCURO)
        dialogo.transient(self)
        dialogo.grab_set()
        dialogo.resizable(False, False)
        marco = tk.Frame(dialogo, bg=GRIS_OSCURO, padx=16, pady=14)
        marco.pack(fill="both", expand=True)
        tk.Label(marco, text="NUEVA LICENCIA", font=("Impact", 14),
                 fg=NEON, bg=GRIS_OSCURO).pack(anchor="w", pady=(0, 8))
        tk.Label(
            marco, text="La clave se genera sola a partir del código de "
                        "instalación que te mandó el profesional.",
            font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
            wraplength=380,
        ).pack(anchor="w", pady=(0, 8))

        campos = {}
        for clave, etiqueta, ancho in (
            ("profesional", "Profesional *:", 34),
            ("contacto", "Contacto (tel/email):", 28),
            ("codigo", "Código de instalación:", 26),
            ("notas", "Notas:", 34),
        ):
            fila = tk.Frame(marco, bg=GRIS_OSCURO)
            fila.pack(fill="x", pady=3)
            tk.Label(fila, text=etiqueta, width=22, anchor="e",
                     font=("Segoe UI", 9, "bold"), fg=BLANCO,
                     bg=GRIS_OSCURO).pack(side="left")
            entrada = tk.Entry(fila, width=ancho, bg=GRIS, fg=BLANCO,
                               insertbackground=NEON, relief="flat")
            entrada.pack(side="left", padx=(8, 0), ipady=3)
            campos[clave] = entrada

        lbl_vista = tk.Label(marco, text="", font=("Consolas", 10, "bold"),
                             fg=AMARILLO, bg=GRIS_OSCURO)
        lbl_vista.pack(anchor="w", pady=(8, 0))

        def ver_clave():
            try:
                clave = licencia.clave_para(campos["codigo"].get())
                lbl_vista.configure(
                    text=f"Clave que le mandarás: {clave}")
            except Exception:
                lbl_vista.configure(text="Código inválido.")

        campos["codigo"].bind("<KeyRelease>", lambda _e: ver_clave())

        def guardar():
            if not campos["profesional"].get().strip():
                messagebox.showwarning("Licencias", "Falta el profesional.",
                                       parent=dialogo)
                return
            codigo = campos["codigo"].get()
            if len(licencia._normalizar(codigo)) < 8:
                messagebox.showwarning(
                    "Licencias", "El código de instalación no es válido.",
                    parent=dialogo)
                return
            registrar_licencia(
                campos["profesional"].get(), campos["contacto"].get(),
                codigo, campos["notas"].get(),
            )
            dialogo.destroy()
            self._refrescar()

        barra = tk.Frame(marco, bg=GRIS_OSCURO)
        barra.pack(fill="x", pady=(12, 0))
        tk.Button(barra, text="GUARDAR", command=guardar, font=("Impact", 12),
                  fg=NEGRO, bg=NEON, activebackground=NARANJA,
                  activeforeground=BLANCO, relief="flat", padx=14, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(barra, text="CANCELAR", command=dialogo.destroy,
                  font=("Impact", 12), fg=NEON, bg=GRIS,
                  activebackground=NARANJA, activeforeground=BLANCO,
                  relief="flat", padx=14, pady=5,
                  cursor="hand2").pack(side="left")
        campos["profesional"].focus_set()
        dialogo.wait_window(dialogo)

    def _registrar_entrega(self):
        lic_id = self._id_seleccionado()
        if not lic_id:
            messagebox.showinfo("Licencias", "Selecciona un profesional.")
            return
        dialogo = tk.Toplevel(self)
        dialogo.title("Registrar entrega / actualización")
        dialogo.configure(bg=GRIS_OSCURO)
        dialogo.transient(self)
        dialogo.grab_set()
        dialogo.resizable(False, False)
        marco = tk.Frame(dialogo, bg=GRIS_OSCURO, padx=16, pady=14)
        marco.pack(fill="both", expand=True)
        tk.Label(marco, text="REGISTRAR ENTREGA", font=("Impact", 14),
                 fg=NEON, bg=GRIS_OSCURO).pack(anchor="w", pady=(0, 8))

        fila_v = tk.Frame(marco, bg=GRIS_OSCURO)
        fila_v.pack(fill="x", pady=3)
        tk.Label(fila_v, text="Versión entregada:", width=18, anchor="e",
                 font=("Segoe UI", 9, "bold"), fg=BLANCO,
                 bg=GRIS_OSCURO).pack(side="left")
        var_version = tk.StringVar(value=VERSION)
        tk.Entry(fila_v, width=12, bg=GRIS, fg=BLANCO, relief="flat",
                 textvariable=var_version).pack(side="left", padx=(8, 0),
                                                ipady=3)
        fila_n = tk.Frame(marco, bg=GRIS_OSCURO)
        fila_n.pack(fill="x", pady=3)
        tk.Label(fila_n, text="Notas:", width=18, anchor="e",
                 font=("Segoe UI", 9, "bold"), fg=BLANCO,
                 bg=GRIS_OSCURO).pack(side="left")
        entrada_notas = tk.Entry(fila_n, width=38, bg=GRIS, fg=BLANCO,
                                 insertbackground=NEON, relief="flat")
        entrada_notas.pack(side="left", padx=(8, 0), ipady=3)

        def guardar():
            registrar_entrega(lic_id, var_version.get(), entrada_notas.get())
            dialogo.destroy()
            self._refrescar()
            self._al_seleccionar()

        barra = tk.Frame(marco, bg=GRIS_OSCURO)
        barra.pack(fill="x", pady=(12, 0))
        tk.Button(barra, text="GUARDAR", command=guardar, font=("Impact", 12),
                  fg=NEGRO, bg=NEON, activebackground=NARANJA,
                  activeforeground=BLANCO, relief="flat", padx=14, pady=5,
                  cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(barra, text="CANCELAR", command=dialogo.destroy,
                  font=("Impact", 12), fg=NEON, bg=GRIS,
                  activebackground=NARANJA, activeforeground=BLANCO,
                  relief="flat", padx=14, pady=5,
                  cursor="hand2").pack(side="left")
        dialogo.wait_window(dialogo)

    def _copiar_clave(self):
        lic_id = self._id_seleccionado()
        if not lic_id:
            messagebox.showinfo("Licencias", "Selecciona un profesional.")
            return
        l = obtener_licencia(lic_id)
        self.clipboard_clear()
        self.clipboard_append(l["clave"])
        messagebox.showinfo(
            "Licencias", f"Clave de {l['profesional']} copiada:\n{l['clave']}"
        )

    def _eliminar(self):
        lic_id = self._id_seleccionado()
        if not lic_id:
            messagebox.showinfo("Licencias", "Selecciona un profesional.")
            return
        l = obtener_licencia(lic_id)
        if messagebox.askyesno(
            "Licencias",
            f"¿Eliminar el registro de {l['profesional']}?\n"
            "La clave deja de verse aquí (el cliente ya activado sigue "
            "funcionando).",
        ):
            eliminar_licencia(lic_id)
            self.lbl_sel.configure(text="—")
            for item in self.tree_entregas.get_children():
                self.tree_entregas.delete(item)
            self._refrescar()


if __name__ == "__main__":
    App().mainloop()
