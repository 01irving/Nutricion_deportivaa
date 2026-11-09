"""
Pestaña Recomendaciones — biblioteca de PDFs en carpetas.

Permite crear carpetas, subir documentos PDF (desde el disco), abrirlos,
imprimirlos con el membrete institucional y eliminarlos, para tener a mano
las recomendaciones que se comparten con el paciente.
"""
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import database
from impresion_utils import abrir_para_imprimir, estampar_membrete
from rutas import base_dir

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

BASE = os.path.join(base_dir(), "recomendaciones")


class RecomendacionesTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  📚 Recomendaciones  ")
        self._pestana = self.marco

        tk.Label(
            self.marco, text="RECOMENDACIONES",
            font=("Impact", 20), fg=NEON, bg=GRIS_OSCURO,
        ).pack(fill="x", pady=(4, 2))

        self.lbl_estado = ttk.Label(
            self.marco, text="Sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        barra = ttk.Frame(self.marco, style="Gym.TFrame")
        barra.pack(fill="x", padx=8, pady=(0, 4))
        for texto, comando, color_fg, color_bg in (
            ("➕ NUEVA CARPETA", self.nueva_carpeta, NEGRO, NEON),
            ("📤 SUBIR PDF", self.subir_pdf, NEGRO, NEON),
            ("🖨 IMPRIMIR CON MEMBRETE", self.imprimir_pdf, NEGRO, NARANJA),
            ("📂 ABRIR", self.abrir_pdf, NEGRO, GRIS),
            ("🗑 ELIMINAR", self.eliminar, NEON, GRIS),
            ("🔄 ACTUALIZAR", self.refrescar, NEON, GRIS),
        ):
            tk.Button(
                barra, text=texto, command=comando,
                font=("Impact", 9), fg=color_fg, bg=color_bg,
                activebackground=NARANJA, activeforeground=BLANCO,
                relief="flat", padx=10, pady=4, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)

        paned = ttk.PanedWindow(self.marco, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- Carpetas ---
        izq = ttk.LabelFrame(paned, text="Carpetas", padding=4)
        paned.add(izq, weight=1)
        self.carpetas_tree = ttk.Treeview(
            izq, show="tree", height=16, style="Gym.Treeview",
            selectmode="browse",
        )
        self.carpetas_tree.tag_configure(
            "carpeta", font=("Segoe UI", 9, "bold"), foreground=NEON)
        sb1 = ttk.Scrollbar(izq, orient=tk.VERTICAL,
                            command=self.carpetas_tree.yview)
        self.carpetas_tree.configure(yscrollcommand=sb1.set)
        self.carpetas_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb1.pack(side=tk.RIGHT, fill=tk.Y)
        self.carpetas_tree.bind("<<TreeviewSelect>>", self._on_carpeta)

        # --- PDFs de la carpeta ---
        der = ttk.LabelFrame(paned, text="Documentos PDF", padding=4)
        paned.add(der, weight=3)
        cols = ("archivo", "kb")
        self.pdf_tree = ttk.Treeview(
            der, columns=cols, show="headings", height=16,
            style="Gym.Treeview", selectmode="browse",
        )
        self.pdf_tree.heading("archivo", text="Documento")
        self.pdf_tree.column("archivo", width=380, anchor=tk.W)
        self.pdf_tree.heading("kb", text="Tamaño (KB)")
        self.pdf_tree.column("kb", width=90, anchor=tk.E)
        sb2 = ttk.Scrollbar(der, orient=tk.VERTICAL,
                            command=self.pdf_tree.yview)
        self.pdf_tree.configure(yscrollcommand=sb2.set)
        self.pdf_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)
        self.pdf_tree.bind("<Double-1>", lambda _e: self.abrir_pdf())

        self._cargar_carpetas()

    # ------------------------------------------------------------------
    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        paciente = database.obtener_paciente(paciente_id) or {}
        self.lbl_estado.configure(
            text=f"Recomendaciones de: "
                 f"{paciente.get('nombre') or paciente_id}")

    def refrescar(self):
        self._cargar_carpetas()

    def _asegurar_base(self):
        os.makedirs(BASE, exist_ok=True)
        return BASE

    def _cargar_carpetas(self):
        base = self._asegurar_base()
        self.carpetas_tree.delete(*self.carpetas_tree.get_children())
        try:
            nombres = sorted(
                n for n in os.listdir(base)
                if os.path.isdir(os.path.join(base, n)))
        except OSError:
            nombres = []
        for n in nombres:
            self.carpetas_tree.insert(
                "", tk.END, iid=n, open=False, text=f"📁 {n}",
                tags=("carpeta",))
        self.pdf_tree.delete(*self.pdf_tree.get_children())

    def _carpeta_seleccionada(self):
        sel = self.carpetas_tree.selection()
        if not sel:
            return None
        return sel[0]

    def _ruta_carpeta(self, nombre):
        return os.path.join(self._asegurar_base(), nombre)

    def _on_carpeta(self, _event=None):
        nombre = self._carpeta_seleccionada()
        self.pdf_tree.delete(*self.pdf_tree.get_children())
        if not nombre:
            return
        ruta = self._ruta_carpeta(nombre)
        try:
            archivos = sorted(
                a for a in os.listdir(ruta)
                if a.lower().endswith(".pdf")
                and os.path.isfile(os.path.join(ruta, a)))
        except OSError:
            archivos = []
        for a in archivos:
            try:
                kb = os.path.getsize(os.path.join(ruta, a)) / 1024
            except OSError:
                kb = 0
            self.pdf_tree.insert("", tk.END, iid=a, open=False,
                                 values=(a, f"{kb:,.0f}"))

    def nueva_carpeta(self):
        from tkinter import simpledialog
        nombre = simpledialog.askstring(
            "Nueva carpeta", "Nombre de la carpeta:", parent=self.marco)
        if not nombre:
            return
        nombre = nombre.strip()
        if not nombre or any(c in nombre for c in '\\/:*?"<>|'):
            messagebox.showwarning(
                "Recomendaciones", "Nombre de carpeta no válido.")
            return
        ruta = self._ruta_carpeta(nombre)
        if os.path.exists(ruta):
            messagebox.showwarning(
                "Recomendaciones", f"La carpeta «{nombre}» ya existe.")
            return
        try:
            os.makedirs(ruta)
        except OSError as error:
            messagebox.showerror("Recomendaciones", str(error))
            return
        self._cargar_carpetas()
        if self.carpetas_tree.exists(nombre):
            self.carpetas_tree.selection_set(nombre)

    def subir_pdf(self):
        nombre = self._carpeta_seleccionada()
        if not nombre:
            messagebox.showwarning(
                "Recomendaciones",
                "Selecciona (o crea) una carpeta primero.")
            return
        rutas = filedialog.askopenfilenames(
            title="Subir PDF",
            filetypes=[("Documentos PDF", "*.pdf")],
            parent=self.marco,
        )
        if not rutas:
            return
        destino = self._ruta_carpeta(nombre)
        copiados = 0
        for ruta in rutas:
            if not os.path.isfile(ruta) or not ruta.lower().endswith(".pdf"):
                continue
            archivo = os.path.basename(ruta)
            objetivo = os.path.join(destino, archivo)
            base, ext = os.path.splitext(archivo)
            cuenta = 2
            while os.path.exists(objetivo):
                objetivo = os.path.join(destino, f"{base} ({cuenta}){ext}")
                cuenta += 1
            try:
                shutil.copy2(ruta, objetivo)
                copiados += 1
            except OSError as error:
                messagebox.showerror(
                    "Recomendaciones",
                    f"No se pudo copiar «{archivo}»:\n{error}")
        self._on_carpeta()
        if copiados:
            messagebox.showinfo(
                "Recomendaciones",
                f"{copiados} PDF agregado(s) a «{nombre}».")

    def _pdf_seleccionado(self):
        sel = self.pdf_tree.selection()
        if not sel:
            return None
        nombre = self._carpeta_seleccionada()
        if not nombre:
            return None
        return os.path.join(self._ruta_carpeta(nombre), sel[0])

    def abrir_pdf(self):
        ruta = self._pdf_seleccionado()
        if not ruta:
            messagebox.showwarning(
                "Recomendaciones", "Selecciona un PDF de la lista.")
            return
        try:
            os.startfile(ruta)  # abre con el visor predeterminado
        except Exception as error:
            messagebox.showerror(
                "Recomendaciones",
                f"No se pudo abrir «{os.path.basename(ruta)}»:\n{error}")

    def imprimir_pdf(self):
        """Abre una copia del PDF con el membrete estampado para imprimir."""
        ruta = self._pdf_seleccionado()
        if not ruta:
            messagebox.showwarning(
                "Recomendaciones", "Selecciona un PDF de la lista.")
            return
        try:
            ruta_membrete = estampar_membrete(ruta)
        except Exception as error:
            messagebox.showwarning(
                "Recomendaciones",
                f"No se pudo estampar el membrete de "
                f"«{os.path.basename(ruta)}»:\n{error}\n\n"
                "Se abrirá el PDF original.")
            ruta_membrete = ruta
        try:
            abrir_para_imprimir(ruta_membrete)
        except Exception as error:
            messagebox.showerror(
                "Recomendaciones",
                f"No se pudo abrir «{os.path.basename(ruta_membrete)}»:\n{error}")

    def eliminar(self):
        """Elimina el PDF seleccionado o, si no hay, la carpeta seleccionada
        (solo si está vacía)."""
        ruta = self._pdf_seleccionado()
        if ruta:
            nombre = os.path.basename(ruta)
            if not messagebox.askyesno(
                    "Recomendaciones",
                    f"¿Eliminar el PDF «{nombre}»?"):
                return
            try:
                os.remove(ruta)
            except OSError as error:
                messagebox.showerror("Recomendaciones", str(error))
                return
            self._on_carpeta()
            return
        nombre = self._carpeta_seleccionada()
        if not nombre:
            messagebox.showwarning(
                "Recomendaciones", "Selecciona un PDF o una carpeta.")
            return
        carpeta = self._ruta_carpeta(nombre)
        try:
            contenido = [a for a in os.listdir(carpeta)
                         if os.path.isfile(os.path.join(carpeta, a))]
        except OSError:
            contenido = []
        if contenido:
            messagebox.showwarning(
                "Recomendaciones",
                f"La carpeta «{nombre}» tiene {len(contenido)} archivo(s).\n"
                "Vacía la carpeta antes de eliminarla.")
            return
        if not messagebox.askyesno(
                "Recomendaciones", f"¿Eliminar la carpeta «{nombre}»?"):
            return
        try:
            os.rmdir(carpeta)
        except OSError as error:
            messagebox.showerror("Recomendaciones", str(error))
            return
        self._cargar_carpetas()
