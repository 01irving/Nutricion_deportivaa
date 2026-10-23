"""
Pestaña Suplementos - Selección de suplementos por categoría.

Permite elegir el suplemento por categoría, consultar la vista previa de
su posología, para qué sirve y los cuidados, y añadirlo a la selección
del paciente activo (persistida en SQLite).
"""
import tkinter as tk
from tkinter import messagebox, ttk

import database
import suplementos_print

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

MOMENTOS = [
    "Antes del entrenamiento",
    "Durante el entrenamiento",
    "Después del entrenamiento",
    "Antes de dormir",
    "Al despertar",
    "Con las comidas",
    "Diario (no conectado al entrenamiento)",
]


class SuplementosTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self.seleccion = []
        self._suplementos = []
        self._por_id = {}

    # ------------------------------------------------------------------
    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  💊 Suplementos  ")

        titulo = tk.Label(
            self.marco,
            text="SUPLEMENTOS DEPORTIVOS",
            font=("Impact", 20), fg=NEON, bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 2))

        self.lbl_estado = ttk.Label(
            self.marco, text="Suplementos: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        paned = ttk.PanedWindow(self.marco, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._crear_panel_catalogo(paned)
        self._crear_panel_seleccion(paned)

    # ------------------------------------------------------------------
    def _crear_panel_catalogo(self, paned):
        left = ttk.LabelFrame(paned, text="Catálogo de suplementos", padding=5)
        paned.add(left, weight=3)

        # --- Filtros: categoría / grupo ---
        filtros = ttk.Frame(left, style="Gym.TFrame")
        filtros.pack(fill="x", pady=2)

        ttk.Label(filtros, text="Categoría:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.categoria_var = tk.StringVar()
        self.categoria_combo = ttk.Combobox(
            filtros, textvariable=self.categoria_var, state="readonly",
            style="Gym.TCombobox", width=32,
        )
        self.categoria_combo.pack(side=tk.LEFT, padx=2)
        self.categoria_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._cargar_suplementos()
        )

        ttk.Label(filtros, text="Grupo IOC:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(10, 2)
        )
        self.grupo_var = tk.StringVar()
        self.grupo_combo = ttk.Combobox(
            filtros, textvariable=self.grupo_var, state="readonly",
            style="Gym.TCombobox", width=26,
        )
        self.grupo_combo.pack(side=tk.LEFT, padx=2)
        self.grupo_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._cargar_suplementos()
        )

        # --- Lista de suplementos ---
        self.tree = ttk.Treeview(
            left, columns=("nombre", "categoria", "grupo"),
            show="headings", height=12, selectmode="browse",
            style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("nombre", "Suplemento", 200),
            ("categoria", "Categoría", 180),
            ("grupo", "Grupo IOC", 170),
        ):
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=ancho, anchor="w")
        vsb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=4)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # --- Datos del suplemento: posología, para qué sirve, cuidados ---
        ttk.Label(
            left, text="VISTA PREVIA", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=4, pady=(4, 2))

        self.lbl_suplemento = tk.Label(
            left, text="", font=("Impact", 13), fg=NEON, bg=GRIS_OSCURO,
            anchor="w",
        )
        self.lbl_suplemento.pack(fill="x", padx=4)

        self.txt_preview = tk.Text(
            left, height=12, wrap=tk.WORD, bg=GRIS_OSCURO, fg=BLANCO,
            insertbackground=NEON, relief="flat", padx=6, pady=4,
            font=("Segoe UI", 9),
        )
        self.txt_preview.pack(fill=tk.BOTH, expand=True, padx=4, pady=3)
        self.txt_preview.configure(state=tk.DISABLED)

        self._cargar_categorias()

    def _crear_panel_seleccion(self, paned):
        right = ttk.LabelFrame(paned, text="Selección del paciente", padding=5)
        paned.add(right, weight=2)

        # --- Datos de la adición ---
        ttk.Label(
            right, text="AÑADIR AL PACIENTE", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=4, pady=2)

        row1 = ttk.Frame(right, style="Gym.TFrame")
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="Momento:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.momento_var = tk.StringVar(value=MOMENTOS[0])
        self.momento_combo = ttk.Combobox(
            row1, textvariable=self.momento_var, state="readonly",
            values=MOMENTOS, style="Gym.TCombobox", width=26,
        )
        self.momento_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        row2 = ttk.Frame(right, style="Gym.TFrame")
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Dosis:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.dosis_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.dosis_var, style="Gym.TEntry").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )

        row3 = ttk.Frame(right, style="Gym.TFrame")
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="Notas:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.notas_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.notas_var, style="Gym.TEntry").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )

        tk.Button(
            row3, text="+ AÑADIR", command=self._anadir,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=3,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=6)

        # --- Lista de la selección ---
        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(
            right, text="SUPLEMENTOS SELECCIONADOS", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=4, pady=2)

        cols = ("nombre", "momento", "dosis")
        self.sel_tree = ttk.Treeview(
            right, columns=cols, show="headings", height=12,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("nombre", "Suplemento", 170),
            ("momento", "Momento", 150),
            ("dosis", "Dosis", 90),
        ):
            self.sel_tree.heading(col, text=texto)
            self.sel_tree.column(col, width=ancho, anchor="w")
        self.sel_tree.column("dosis", anchor="center")
        vsb2 = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.sel_tree.yview)
        self.sel_tree.configure(yscrollcommand=vsb2.set)
        self.sel_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=3)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)

        btns = ttk.Frame(right, style="Gym.TFrame")
        btns.pack(fill="x", pady=2)
        for texto, cmd in (
            ("ELIMINAR SELECCIONADO", self._eliminar),
            ("GUARDAR", self.guardar),
            ("IMPRIMIR", self.imprimir),
            ("LIMPIAR LISTA", self.limpiar),
            ("BORRAR DEL PACIENTE", self.borrar_del_paciente),
        ):
            es_guardar = texto == "GUARDAR"
            es_imprimir = texto == "IMPRIMIR"
            if es_guardar:
                fg, bg, act_bg, act_fg = NEGRO, NARANJA, NEON, NEGRO
            elif es_imprimir:
                fg, bg, act_bg, act_fg = NEGRO, NEON, NARANJA, BLANCO
            else:
                fg, bg, act_bg, act_fg = NEON, GRIS, NARANJA, BLANCO
            tk.Button(
                btns, text=texto, command=cmd,
                font=("Impact", 9),
                fg=fg,
                bg=bg,
                activebackground=act_bg,
                activeforeground=act_fg,
                relief="flat", padx=9, pady=3, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------
    # Catálogo
    # ------------------------------------------------------------------
    def _cargar_categorias(self):
        categorias = database.get_suplementos_categorias()
        self.categoria_combo["values"] = ["Todas las categorías"] + categorias
        self.categoria_combo.current(0)
        grupos = database.get_suplementos_grupos()
        self.grupo_combo["values"] = ["Todos los grupos"] + grupos
        self.grupo_combo.current(0)
        self._cargar_suplementos()

    def _cargar_suplementos(self):
        categoria = self.categoria_var.get()
        grupo = self.grupo_var.get()
        self._suplementos = database.get_suplementos(
            categoria=None if categoria.startswith("Todas") else categoria,
            grupo=None if grupo.startswith("Todos") else grupo,
        )
        self._por_id = {s["id_suplemento"]: s for s in self._suplementos}
        for item in self.tree.get_children():
            self.tree.delete(item)
        for s in self._suplementos:
            self.tree.insert(
                "", tk.END, iid=str(s["id_suplemento"]),
                values=(s["nombre"], s["categoria"], s["grupo"]),
            )

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        sup = self._por_id.get(int(sel[0]))
        if not sup:
            return
        self.lbl_suplemento.configure(text=sup["nombre"].upper())
        self._set_preview(
            f"POSOLOGÍA\n{sup['posologia']}\n\n"
            f"PARA QUÉ SIRVE\n{sup['para_que_sirve']}\n\n"
            f"CUIDADOS Y PRECAUCIONES\n{sup['cuidados']}"
        )

    def _set_preview(self, texto):
        self.txt_preview.configure(state=tk.NORMAL)
        self.txt_preview.delete("1.0", tk.END)
        self.txt_preview.insert("1.0", texto)
        self.txt_preview.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Selección
    # ------------------------------------------------------------------
    def _anadir(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "Suplementos", "Selecciona un paciente antes de añadir."
            )
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Suplementos", "Selecciona un suplemento del catálogo."
            )
            return
        sup = self._por_id.get(int(sel[0]))
        if not sup:
            return
        registro = {
            "paciente_id": self.paciente_id,
            "id_suplemento": sup["id_suplemento"],
            "nombre": sup["nombre"],
            "categoria": sup["categoria"],
            "posologia": sup["posologia"],
            "momento": self.momento_var.get(),
            "dosis": self.dosis_var.get().strip(),
            "notas": self.notas_var.get().strip(),
        }
        self.seleccion.append(registro)
        self._render_seleccion()
        self.dosis_var.set("")
        self.notas_var.set("")

    def _eliminar(self):
        sel = self.sel_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Suplementos", "Selecciona un suplemento de la lista."
            )
            return
        pos = int(sel[0])
        if 0 <= pos < len(self.seleccion):
            self.seleccion.pop(pos)
        self._render_seleccion()

    def _render_seleccion(self):
        for item in self.sel_tree.get_children():
            self.sel_tree.delete(item)
        for i, reg in enumerate(self.seleccion):
            self.sel_tree.insert(
                "", tk.END, iid=str(i),
                values=(
                    reg["nombre"],
                    reg["momento"],
                    reg["dosis"] or "-",
                ),
            )

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def guardar(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "Suplementos", "Selecciona un paciente antes de guardar."
            )
            return
        try:
            database.delete_suplementos_paciente(self.paciente_id)
            for reg in self.seleccion:
                database.insert_suplemento_paciente(reg)
        except Exception as error:
            messagebox.showerror(
                "Suplementos", f"No se pudo guardar:\n{error}"
            )
            return
        messagebox.showinfo(
            "Suplementos",
            f"Guardados {len(self.seleccion)} suplemento(s) para el "
            "paciente activo.",
        )

    def imprimir(self):
        """Genera el PDF del reporte y lo abre para impresión."""
        if self.paciente_id is None:
            messagebox.showwarning(
                "Suplementos", "Selecciona un paciente antes de imprimir."
            )
            return
        if not self.seleccion:
            messagebox.showwarning(
                "Suplementos",
                "No hay suplementos seleccionados para imprimir.",
            )
            return

        paciente = database.obtener_paciente(self.paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{self.paciente_id}"
        ruta = suplementos_print.ruta_temporal_pdf(nombre)
        try:
            supplements_por_id = {
                s["id_suplemento"]: s
                for s in database.get_suplementos()
            }
            suplementos_print.generar_pdf_suplementos(
                ruta, paciente, self.seleccion,
                supplements_por_id=supplements_por_id,
            )
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            suplementos_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
            )
            return

        messagebox.showinfo(
            "Imprimir",
            f"Reporte generado:\n{ruta}\n\n"
            "Incluye nombre, edad, dirección y fecha de impresión.",
        )

    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        self.lbl_estado.configure(text=f"Suplementos de paciente {paciente_id}")
        self.seleccion = database.get_suplementos_paciente(paciente_id)
        self._render_seleccion()

    def refrescar_estado(self):
        """Refresca la lista al entrar en la pestaña (respaldo del paciente activo)."""
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            return
        if paciente_id == self.paciente_id:
            return
        self.cargar(paciente_id)

    def limpiar(self):
        """Vacía la lista de trabajo (no borra lo guardado en la BD)."""
        self.seleccion = []
        self._render_seleccion()

    def desvincular(self):
        """Desvincula el paciente activo y vacía la lista."""
        self.paciente_id = None
        self.seleccion = []
        self._render_seleccion()
        self.lbl_estado.configure(text="Suplementos: sin paciente seleccionado")

    def borrar_del_paciente(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "Suplementos", "Selecciona un paciente antes de borrar."
            )
            return
        if not messagebox.askyesno(
            "Suplementos",
            "Se borrarán todos los suplementos guardados de este paciente. "
            "¿Continuar?",
        ):
            return
        database.delete_suplementos_paciente(self.paciente_id)
        self.seleccion = []
        self._render_seleccion()
        messagebox.showinfo(
            "Suplementos", "Suplementos eliminados del paciente."
        )
