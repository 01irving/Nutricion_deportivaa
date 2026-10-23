"""
Pestaña Estiramientos - Catálogo de estiramientos por grupo muscular.

Permite elegir el grupo muscular, consultar la vista previa del ejercicio
(ilustración, forma de ejecución, músculos estirados, variantes,
observaciones y advertencias) y añadirlo a la selección del paciente
activo (persistida en SQLite).
"""
import io
import os
import tkinter as tk
from tkinter import messagebox, ttk

import database
import estiramientos_print

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

RUTA_IMAGENES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "estiramientos_img"
)

MOMENTOS = [
    "Antes del entrenamiento",
    "Durante el calentamiento",
    "Entre series",
    "Después del entrenamiento",
    "Antes de dormir",
    "Al despertar",
    "Diario (fuera del entrenamiento)",
]

DURACIONES = [
    "10 segundos",
    "15 segundos",
    "20 segundos",
    "30 segundos",
    "1 minuto",
]


class EstiramientosTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self.seleccion = []
        self._estiramientos = []
        self._por_id = {}
        self._foto = None
        self._dirty = False

    # ------------------------------------------------------------------
    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  🧘 Estiramientos  ")

        titulo = tk.Label(
            self.marco,
            text="ESTIRAMIENTOS POR GRUPO MUSCULAR",
            font=("Impact", 20), fg=NEON, bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 2))

        self.lbl_estado = ttk.Label(
            self.marco, text="Estiramientos: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        paned = ttk.PanedWindow(self.marco, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._crear_panel_catalogo(paned)
        self._crear_panel_seleccion(paned)

    # ------------------------------------------------------------------
    def _crear_panel_catalogo(self, paned):
        left = ttk.LabelFrame(paned, text="Catálogo de estiramientos", padding=5)
        paned.add(left, weight=3)

        # --- Filtro por grupo muscular ---
        filtros = ttk.Frame(left, style="Gym.TFrame")
        filtros.pack(fill="x", pady=2)

        ttk.Label(filtros, text="Grupo muscular:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.grupo_var = tk.StringVar()
        self.grupo_combo = ttk.Combobox(
            filtros, textvariable=self.grupo_var, state="readonly",
            style="Gym.TCombobox", width=24,
        )
        self.grupo_combo.pack(side=tk.LEFT, padx=2)
        self.grupo_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._cargar_estiramientos()
        )

        # --- Lista de ejercicios ---
        self.tree = ttk.Treeview(
            left, columns=("numero", "nombre", "grupo"),
            show="headings", height=8, selectmode="browse",
            style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("numero", "#", 40),
            ("nombre", "Ejercicio", 300),
            ("grupo", "Grupo", 120),
        ):
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=ancho, anchor="w")
        self.tree.column("numero", anchor="center")
        vsb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=4)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # --- Vista previa: ilustración + descripción ---
        ttk.Label(
            left, text="FORMA DE REALIZACIÓN", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=4, pady=(6, 2))

        self.lbl_estiramiento = tk.Label(
            left, text="", font=("Impact", 13), fg=NEON, bg=GRIS_OSCURO,
            anchor="w",
        )
        self.lbl_estiramiento.pack(fill="x", padx=4)

        marco_preview = ttk.Frame(left, style="Gym.TFrame")
        marco_preview.pack(fill=tk.BOTH, expand=True, padx=4, pady=3)

        self.lbl_imagen = tk.Label(
            marco_preview, text="", bg=GRIS_OSCURO, relief="flat",
        )
        self.lbl_imagen.pack(side=tk.LEFT, padx=(0, 6))

        self.txt_preview = tk.Text(
            marco_preview, height=13, width=46, wrap=tk.WORD,
            bg=GRIS_OSCURO, fg=BLANCO, insertbackground=NEON,
            relief="flat", padx=6, pady=4, font=("Segoe UI", 9),
        )
        self.txt_preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.txt_preview.configure(state=tk.DISABLED)

        self._cargar_grupos()

    def _crear_panel_seleccion(self, paned):
        right = ttk.LabelFrame(paned, text="Selección del paciente", padding=5)
        paned.add(right, weight=2)

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
        ttk.Label(row2, text="Duración:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.duracion_var = tk.StringVar(value=DURACIONES[1])
        self.duracion_combo = ttk.Combobox(
            row2, textvariable=self.duracion_var, state="readonly",
            values=DURACIONES, style="Gym.TCombobox", width=14,
        )
        self.duracion_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(row2, text="Notas:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(10, 2)
        )
        self.notas_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.notas_var, style="Gym.TEntry").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )

        tk.Button(
            row2, text="+ AÑADIR", command=self._anadir,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=3,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=6)

        # --- Lista de la selección ---
        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(
            right, text="ESTIRAMIENTOS SELECCIONADOS", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=4, pady=2)

        self.sel_tree = ttk.Treeview(
            right, columns=("nombre", "momento", "duracion"), show="headings",
            height=12, selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("nombre", "Estiramiento", 170),
            ("momento", "Momento", 140),
            ("duracion", "Duración", 90),
        ):
            self.sel_tree.heading(col, text=texto)
            self.sel_tree.column(col, width=ancho, anchor="w")
        self.sel_tree.column("duracion", anchor="center")
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
    def _cargar_grupos(self):
        grupos = database.get_estiramientos_grupos()
        self.grupo_combo["values"] = ["Todos los grupos"] + grupos
        self.grupo_combo.current(0)
        self._cargar_estiramientos()

    def _cargar_estiramientos(self):
        grupo = self.grupo_var.get()
        self._estiramientos = database.get_estiramientos(
            grupo=None if grupo.startswith("Todos") else grupo
        )
        self._por_id = {e["id_estiramiento"]: e for e in self._estiramientos}
        for item in self.tree.get_children():
            self.tree.delete(item)
        for e in self._estiramientos:
            self.tree.insert(
                "", tk.END, iid=str(e["id_estiramiento"]),
                values=(e["numero"], e["nombre"], e["grupo"]),
            )

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        ejercicio = self._por_id.get(int(sel[0]))
        if not ejercicio:
            return
        self.lbl_estiramiento.configure(text=ejercicio["nombre"].upper())
        self._set_preview(ejercicio)
        self._cargar_imagen(ejercicio)

    def _set_preview(self, ejercicio):
        partes = [
            f"CÓMO REALIZARLO\n{ejercicio['descripcion'] or '-'}",
            f"MÚSCULOS ESTIRADOS\n{ejercicio['musculos'] or '-'}",
        ]
        if ejercicio.get("variantes"):
            partes.append(f"VARIANTES\n{ejercicio['variantes']}")
        if ejercicio.get("observaciones"):
            partes.append(f"OBSERVACIONES\n{ejercicio['observaciones']}")
        if ejercicio.get("atencion"):
            partes.append(f"ATENCIÓN\n{ejercicio['atencion']}")
        if ejercicio.get("rotulos"):
            partes.append(f"RÓTULOS DE LA ILUSTRACIÓN\n{ejercicio['rotulos']}")
        texto = "\n\n".join(partes)
        self.txt_preview.configure(state=tk.NORMAL)
        self.txt_preview.delete("1.0", tk.END)
        self.txt_preview.insert("1.0", texto)
        self.txt_preview.configure(state=tk.DISABLED)

    def _cargar_imagen(self, ejercicio):
        """Muestra la ilustración: primero el blob de la base, luego el archivo."""
        self.lbl_imagen.configure(image="", text="")
        self._foto = None
        try:
            from PIL import Image, ImageTk
        except Exception:
            return

        original = None
        blob = ejercicio.get("imagen_blob")
        if blob:
            try:
                with Image.open(io.BytesIO(blob)) as imagen:
                    original = imagen.convert("RGB")
            except Exception:
                original = None

        if original is None:
            nombre = ejercicio.get("imagen")
            if not nombre:
                return
            for ext in (".png", ".jpg", ".jpeg"):
                ruta = os.path.join(RUTA_IMAGENES, f"{nombre}{ext}")
                if os.path.exists(ruta):
                    try:
                        with Image.open(ruta) as imagen:
                            original = imagen.convert("RGB")
                    except Exception:
                        original = None
                    break
        if original is None:
            return

        copia = original.copy()
        copia.thumbnail((260, 300))
        self._foto = ImageTk.PhotoImage(copia)
        self.lbl_imagen.configure(image=self._foto, text="")

    # ------------------------------------------------------------------
    # Selección
    # ------------------------------------------------------------------
    def _anadir(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de añadir."
            )
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un estiramiento del catálogo."
            )
            return
        ejercicio = self._por_id.get(int(sel[0]))
        if not ejercicio:
            return
        registro = {
            "paciente_id": self.paciente_id,
            "id_estiramiento": ejercicio["id_estiramiento"],
            "grupo": ejercicio["grupo"],
            "nombre": ejercicio["nombre"],
            "momento": self.momento_var.get(),
            "duracion": self.duracion_var.get().strip(),
            "notas": self.notas_var.get().strip(),
        }
        self.seleccion.append(registro)
        self._dirty = True
        self._render_seleccion()
        self.notas_var.set("")

    def _eliminar(self):
        sel = self.sel_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un estiramiento de la lista."
            )
            return
        pos = int(sel[0])
        if 0 <= pos < len(self.seleccion):
            self.seleccion.pop(pos)
        self._dirty = True
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
                    reg["duracion"] or "-",
                ),
            )

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def guardar(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de guardar."
            )
            return
        try:
            database.delete_estiramientos_paciente(self.paciente_id)
            for reg in self.seleccion:
                database.insert_estiramiento_paciente(reg)
        except Exception as error:
            messagebox.showerror(
                "Estiramientos", f"No se pudo guardar:\n{error}"
            )
            return
        self._dirty = False
        messagebox.showinfo(
            "Estiramientos",
            f"Guardados {len(self.seleccion)} estiramiento(s) para el "
            "paciente activo.",
        )

    def imprimir(self):
        """Genera el PDF del reporte y lo abre para impresión."""
        if self.paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de imprimir."
            )
            return
        if not self.seleccion:
            messagebox.showwarning(
                "Estiramientos",
                "No hay estiramientos seleccionados para imprimir.",
            )
            return

        paciente = database.obtener_paciente(self.paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{self.paciente_id}"
        ruta = estiramientos_print.ruta_temporal_pdf(nombre)
        try:
            catalogo = {
                e["id_estiramiento"]: e for e in database.get_estiramientos()
            }
            estiramientos_print.generar_pdf_estiramientos(
                ruta, paciente, self.seleccion,
                estiramientos_por_id=catalogo,
            )
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            estiramientos_print.abrir_para_imprimir(ruta)
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
            "Incluye membrete, datos del paciente, ilustraciones y fecha.",
        )

    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        self.lbl_estado.configure(text=f"Estiramientos de paciente {paciente_id}")
        self.seleccion = database.get_estiramientos_paciente(paciente_id)
        self._dirty = False
        self._render_seleccion()

    def refrescar_estado(self):
        """Refresca la lista al entrar en la pestaña (respaldo del paciente activo)."""
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            return
        if paciente_id == self.paciente_id:
            # Si no hay cambios sin guardar, refleja lo que se haya añadido
            # desde la pestaña Rutinas > Estiramiento.
            if not self._dirty:
                self.cargar(paciente_id)
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
        self.lbl_estado.configure(text="Estiramientos: sin paciente seleccionado")

    def borrar_del_paciente(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de borrar."
            )
            return
        if not messagebox.askyesno(
            "Estiramientos",
            "Se borrarán todos los estiramientos guardados de este paciente. "
            "¿Continuar?",
        ):
            return
        database.delete_estiramientos_paciente(self.paciente_id)
        self.seleccion = []
        self._render_seleccion()
        messagebox.showinfo(
            "Estiramientos", "Estiramientos eliminados del paciente."
        )
