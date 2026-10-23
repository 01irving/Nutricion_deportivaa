import io
import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

try:  # Tk nativo solo decodifica PNG/GIF; Pillow permite leer el JPEG guardado en la BD
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - entorno sin Pillow
    Image = None
    ImageTk = None

import database
from estiramientos_tab import DURACIONES, MOMENTOS

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

RUTA_IMAGENES = os.path.join(os.path.dirname(__file__), "assets", "rutinas")
CATALOGOS_JSON = {
    "hombros": "hombros_ejercicios.json",
    "brazos": "brazos_ejercicios.json",
}
GRUPOS_PREFERIDOS = ("hombros", "brazos")

TAMANO_IMG_RESPALDO = (560, 380)


class RutinasTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self.grupo = "hombros"
        self.grupos = []
        self.ejercicios = []
        self.est_catalogo = []
        self.est_actual = None
        self.est_seleccion = []
        self._est_foto = None
        self._cargar_grupos()
        self._cargar_ejercicios()
        self.imagen_actual = None
        self._img_origen = None
        self._img_fuente = ""
        self._tam_panel = TAMANO_IMG_RESPALDO
        self._img_after = None
        self.ejercicio_seleccionado = None

    def _cargar_grupos(self):
        """Grupos musculares disponibles en la base, con hombros primero."""
        try:
            filas = database.get_rutinas_grupos()
        except Exception:
            filas = []
        filas.sort(
            key=lambda f: (
                GRUPOS_PREFERIDOS.index(f["grupo"])
                if f["grupo"] in GRUPOS_PREFERIDOS
                else len(GRUPOS_PREFERIDOS),
                f["grupo"],
            )
        )
        self.grupos = filas or [{"grupo": "hombros", "total": 0}]
        disponibles = [g["grupo"] for g in self.grupos]
        if self.grupo not in disponibles:
            self.grupo = disponibles[0]

    def _cargar_ejercicios(self, grupo=None):
        """Lee los ejercicios (imagen + descripción) del grupo desde la base única."""
        self.grupo = grupo or self.grupo or "hombros"
        try:
            filas = database.get_rutinas_ejercicios(self.grupo)
            if filas:
                self.ejercicios = filas
                return
        except Exception:
            pass
        # Respaldo: JSON local si la base no responde o está vacía
        nombre_json = CATALOGOS_JSON.get(self.grupo, "")
        ruta_json = os.path.join(os.path.dirname(__file__), nombre_json) if nombre_json else ""
        for codificacion in ("utf-8-sig", "utf-8"):
            try:
                with open(ruta_json, "r", encoding=codificacion) as f:
                    self.ejercicios = json.load(f)
                return
            except Exception:
                continue
        self.ejercicios = []

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  Rutinas  ")

        fila_titulo = ttk.Frame(self.marco, style="Gym.TFrame")
        fila_titulo.pack(fill="x", pady=(2, 0))

        self.titulo = tk.Label(
            fila_titulo,
            text=f"RUTINAS · {self.grupo.upper()}",
            font=("Impact", 15),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        self.titulo.pack(side="left", fill="x", expand=True)

        self.lbl_grupo_titulo = tk.Label(
            fila_titulo,
            text="Grupo:",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        )
        self.lbl_grupo_titulo.pack(side="left", padx=(0, 4))
        self.grupo_combo = ttk.Combobox(
            fila_titulo,
            values=[g["grupo"].capitalize() for g in self.grupos],
            state="readonly",
            width=12,
            style="Gym.TCombobox",
        )
        self.grupo_combo.pack(side="left", padx=(0, 8), pady=2)
        self.grupo_combo.set(self.grupo.capitalize())
        self.grupo_combo.bind("<<ComboboxSelected>>", self._al_cambiar_grupo)

        self.lbl_estado = ttk.Label(
            self.marco,
            text="Rutinas: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        self.notebook_rut = ttk.Notebook(self.marco)
        self.notebook_rut.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._crear_tab_calentamiento()
        self._crear_tab_rutina()
        self._crear_tab_estiramiento()
        self.notebook_rut.bind("<<NotebookTabChanged>>", self._al_cambiar_subpestana)
        self.cargar(getattr(self.app, "id_paciente_antro", None))

    def _crear_tab_calentamiento(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Calentamiento  ")
        tk.Label(
            marco,
            text="Calentamiento general/articular para hombros",
            font=("Segoe UI", 10),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=10, pady=(8, 4))
        self.frame_calent = ttk.Frame(marco, style="Gym.TFrame")
        self.frame_calent.pack(fill="both", expand=True, padx=10, pady=4)

    def _crear_tab_rutina(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Rutina  ")

        contenedor_principal = ttk.Frame(marco, style="Gym.TFrame")
        contenedor_principal.pack(fill="both", expand=True, padx=10, pady=(2, 6))

        superior = ttk.Frame(contenedor_principal, style="Gym.TFrame")

        panel_sel = ttk.LabelFrame(superior, text="Seleccionar ejercicio", padding=6)
        panel_sel.pack(side="left", fill="y", padx=(0, 6))

        self.combo_ej = ttk.Combobox(
            panel_sel, values=[], width=46, state="readonly", style="Gym.TCombobox"
        )
        self.combo_ej.pack()
        self.combo_ej.bind("<<ComboboxSelected>>", self._al_seleccionar_combo)

        self.lbl_catalogo = tk.Label(
            panel_sel,
            text="",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
            justify="left",
        )
        self.lbl_catalogo.pack(anchor="w", pady=(6, 0))

        marco_desc = ttk.LabelFrame(
            panel_sel, text="Descripción guardada en la base de datos", padding=4
        )
        marco_desc.pack(fill="both", expand=True, pady=(10, 0))

        self.txt_preview_desc = tk.Text(
            marco_desc,
            width=32,
            height=8,
            wrap="word",
            bg=GRIS_OSCURO,
            fg=BLANCO,
            relief="flat",
            padx=6,
            pady=4,
            font=("Segoe UI", 9),
            highlightthickness=0,
        )
        self.txt_preview_desc.configure(state="disabled")
        barra_desc = ttk.Scrollbar(marco_desc, orient="vertical", command=self.txt_preview_desc.yview)
        self.txt_preview_desc.configure(yscrollcommand=barra_desc.set)
        self.txt_preview_desc.pack(side="left", fill="both", expand=True)
        barra_desc.pack(side="right", fill="y")

        panel_der = ttk.LabelFrame(
            superior,
            text="Previsualización (imagen desde la base de datos)",
            padding=6,
        )
        panel_der.pack(side="right", fill="both", expand=True)

        self.lbl_preview_titulo = tk.Label(
            panel_der,
            text="Selecciona un ejercicio de la lista desplegable",
            font=("Segoe UI", 10, "bold"),
            fg=NEON,
            bg=GRIS_OSCURO,
            anchor="w",
            justify="left",
        )
        self.lbl_preview_titulo.pack(fill="x")

        cont_img = ttk.Frame(panel_der, style="Gym.TFrame")
        cont_img.pack(fill="both", expand=True, pady=(4, 2))
        cont_img.bind("<Configure>", self._al_redimensionar)
        self._contenedor_img = cont_img

        self.lbl_preview_img = tk.Label(
            cont_img,
            bg=GRIS_OSCURO,
            text="",
            fg=GRIS_TEXTO,
            font=("Segoe UI", 9),
        )
        self.lbl_preview_img.pack(expand=True)

        self.lbl_preview_fuente = tk.Label(
            panel_der,
            text="",
            font=("Segoe UI", 7),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
            anchor="w",
        )
        self.lbl_preview_fuente.pack(fill="x")

        # --- Series / repeticiones del ejercicio seleccionado ---
        marco_registro = ttk.LabelFrame(
            contenedor_principal,
            text="Series / Repeticiones / Descanso / Peso del ejercicio seleccionado",
            padding=6,
        )

        campos = ttk.Frame(marco_registro, style="Gym.TFrame")
        campos.pack(fill="x")
        self.reg_entradas = {}
        for c, (texto, ancho, inicial) in enumerate(
            [
                ("Series", 6, "3"),
                ("Repeticiones", 8, "12"),
                ("Descanso entre repeticiones (seg)", 10, ""),
                ("Descanso entre series (seg)", 10, ""),
                ("Peso (kg)", 8, ""),
            ]
        ):
            f = ttk.Frame(campos, style="Gym.TFrame")
            f.grid(row=0, column=c, padx=6)
            tk.Label(f, text=texto, font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO).pack(anchor="w")
            e = ttk.Entry(f, width=ancho, style="Gym.TEntry")
            e.pack()
            if inicial:
                e.insert(0, inicial)
            self.reg_entradas[texto] = e

        boton_alta = ttk.Frame(campos, style="Gym.TFrame")
        boton_alta.grid(row=0, column=5, padx=(14, 4), sticky="s")
        tk.Button(
            boton_alta,
            text="+ AÑADIR A LA RUTINA",
            command=self._anadir_ejercicio,
            font=("Impact", 10),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
        ).pack()

        # --- Rutina acumulada del paciente ---
        marco_rutina_pac = ttk.LabelFrame(
            contenedor_principal, text="Rutina del paciente", padding=6
        )

        cols = ("num", "nombre", "equipo", "series", "reps", "desc_rep", "desc_serie", "peso")
        self.tree_rutina = ttk.Treeview(
            marco_rutina_pac,
            columns=cols,
            show="headings",
            height=4,
            selectmode="browse",
            style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("num", "#", 34, "center"),
            ("nombre", "Ejercicio", 200, "w"),
            ("equipo", "Equipo", 100, "w"),
            ("series", "Series", 52, "center"),
            ("reps", "Reps", 52, "center"),
            ("desc_rep", "Desc. rep (s)", 100, "center"),
            ("desc_serie", "Desc. serie (s)", 104, "center"),
            ("peso", "Peso (kg)", 68, "center"),
        ):
            self.tree_rutina.heading(col, text=texto, anchor=alineacion)
            self.tree_rutina.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion,
                stretch=(col == "nombre"),
            )
        barra_rutina = ttk.Scrollbar(
            marco_rutina_pac, orient="vertical", command=self.tree_rutina.yview
        )
        self.tree_rutina.configure(yscrollcommand=barra_rutina.set)
        self.tree_rutina.pack(side="left", fill="both", expand=True)
        barra_rutina.pack(side="left", fill="y")

        acciones = ttk.Frame(marco_rutina_pac, style="Gym.TFrame")
        acciones.pack(side="left", fill="y", padx=(8, 0))
        tk.Button(
            acciones,
            text="Quitar seleccionado",
            command=self._quitar_ejercicio,
            font=("Segoe UI", 8, "bold"),
            fg=BLANCO,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
        ).pack(fill="x", pady=(0, 4))
        tk.Button(
            acciones,
            text="Vaciar rutina",
            command=self._vaciar_rutina,
            font=("Segoe UI", 8, "bold"),
            fg=BLANCO,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=2,
            cursor="hand2",
        ).pack(fill="x")
        self.lbl_rutina_total = ttk.Label(
            acciones, text="0 ejercicios", style="Estado.TLabel"
        )
        self.lbl_rutina_total.pack(anchor="w", pady=(8, 0))

        # Primero reservan su espacio la tabla y el registro; el panel de
        # seleccion/previsualizacion se queda con el resto
        marco_rutina_pac.pack(side="bottom", fill="both", pady=(6, 0))
        marco_registro.pack(side="bottom", fill="x", pady=(6, 0))
        superior.pack(fill="both", expand=True)

        self._poblar_combo_ejercicios()

    def _poblar_combo_ejercicios(self):
        opciones = [
            f"{ej.get('num','')}. {ej.get('nombre','')} ({ej.get('equipo') or '-'})"
            for ej in self.ejercicios
        ]
        self.combo_ej.configure(values=opciones)
        self.lbl_catalogo.configure(
            text=f"{len(self.ejercicios)} ejercicios · {database.DB_PATH.name}"
        )
        if self.ejercicios:
            self.combo_ej.current(0)
            self._al_seleccionar_combo()
        else:
            self.ejercicio_seleccionado = None
            self.combo_ej.set("")
            self.lbl_preview_titulo.configure(
                text=f"Sin ejercicios cargados para {self.grupo}"
            )
            self._mostrar_descripcion({})
            self.lbl_preview_img.configure(image="", text="")
            self.lbl_preview_fuente.configure(text="")

    def _al_cambiar_grupo(self, event=None):
        elegido = self.grupo_combo.get().strip().lower()
        if not elegido or elegido == self.grupo:
            return
        self._cargar_ejercicios(elegido)
        if self._subpestana_actual() != 2:
            self.titulo.configure(text=f"RUTINAS · {self.grupo.upper()}")
        self._poblar_combo_ejercicios()

    def _subpestana_actual(self):
        try:
            return self.notebook_rut.index("current")
        except Exception:
            return 1

    def _al_cambiar_subpestana(self, event=None):
        """En Estiramientos el título y el filtro de grupo son otros."""
        if self._subpestana_actual() == 2:
            self.titulo.configure(text="ESTIRAMIENTOS")
            self.lbl_grupo_titulo.pack_forget()
            self.grupo_combo.pack_forget()
            self._cargar_est_paciente()
        else:
            self.titulo.configure(text=f"RUTINAS · {self.grupo.upper()}")
            if not self.lbl_grupo_titulo.winfo_ismapped():
                self.lbl_grupo_titulo.pack(side="left", padx=(0, 4))
                self.grupo_combo.pack(side="left", padx=(0, 8), pady=2)

    def _al_seleccionar_combo(self, event=None):
        idx = self.combo_ej.current()
        if idx < 0 or idx >= len(self.ejercicios):
            return
        ej = self.ejercicios[idx]
        self.ejercicio_seleccionado = ej
        self._mostrar_ejercicio(ej)

    def _mostrar_ejercicio(self, ej):
        self.lbl_preview_titulo.configure(
            text=f"{ej.get('num','')}. {ej.get('nombre','')}  |  Equipo: {ej.get('equipo') or '-'}"
        )
        self._mostrar_descripcion(ej)
        self._cargar_imagen(ej)

    def _mostrar_descripcion(self, ej):
        texto = (ej.get("descripcion") or "").strip()
        if not texto:
            texto = "Este ejercicio no tiene descripción guardada en la base de datos."
        self.txt_preview_desc.configure(state="normal")
        self.txt_preview_desc.delete("1.0", "end")
        self.txt_preview_desc.insert("1.0", texto)
        self.txt_preview_desc.configure(state="disabled")

    def _cargar_imagen(self, ej):
        """Usa el blob guardado en la BD y, si faltara, el archivo del disco."""
        self._img_origen = None
        self.imagen_actual = None
        self._img_fuente = ""
        self.lbl_preview_img.configure(image="", text="")
        self.lbl_preview_fuente.configure(text="")

        if Image is None:
            self.lbl_preview_img.configure(
                text="Pillow no está instalado: no se pueden mostrar las imágenes JPEG."
            )
            return

        blob = ej.get("imagen_blob")
        if blob:
            try:
                with Image.open(io.BytesIO(blob)) as imagen:
                    self._img_origen = imagen.convert("RGB")
                self._img_fuente = f"BD · imagen_blob ({len(blob) / 1024:.0f} KB)"
            except Exception:
                self._img_origen = None

        if self._img_origen is None:
            nombre = ej.get("imagen_nombre") or ej.get("imagen") or ""
            ruta = os.path.join(RUTA_IMAGENES, self.grupo, nombre) if nombre else ""
            if ruta and os.path.exists(ruta):
                try:
                    with Image.open(ruta) as imagen:
                        self._img_origen = imagen.convert("RGB")
                    self._img_fuente = f"archivo · {nombre}"
                except Exception:
                    self._img_origen = None

        if self._img_origen is None:
            self.lbl_preview_img.configure(text="Sin imagen asociada a este ejercicio")
            return

        ancho, alto = self._img_origen.size
        self.lbl_preview_fuente.configure(
            text=f"Imagen desde {self._img_fuente} · original {ancho}x{alto} px"
        )
        self._render_imagen()

    def _al_redimensionar(self, event):
        if event.width < 40 or event.height < 40:
            return
        self._tam_panel = (event.width, event.height)
        self.lbl_preview_titulo.configure(wraplength=max(event.width - 20, 200))
        if self._img_after is not None:
            try:
                self.lbl_preview_img.after_cancel(self._img_after)
            except Exception:
                pass
        self._img_after = self.lbl_preview_img.after(140, self._render_imagen)

    def _render_imagen(self):
        self._img_after = None
        if self._img_origen is None:
            return
        if not self.lbl_preview_img.winfo_exists():
            return
        if ImageTk is None:
            self.lbl_preview_img.configure(
                image="", text="Pillow no está instalado: no se pueden mostrar las imágenes JPEG."
            )
            return
        ancho, alto = self._tam_panel
        ancho = max(int(ancho) - 12, 120)
        alto = max(int(alto) - 12, 120)
        copia = self._img_origen.copy()
        copia.thumbnail((ancho, alto), Image.LANCZOS)
        self.imagen_actual = ImageTk.PhotoImage(copia)
        self.lbl_preview_img.configure(image=self.imagen_actual, text="")

    def _crear_tab_estiramiento(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Estiramiento  ")

        contenedor = ttk.Frame(marco, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=10, pady=(2, 6))

        # --- Filtros ---
        filtros = ttk.Frame(contenedor, style="Gym.TFrame")
        tk.Label(
            filtros, text="Grupo:", font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
        ).pack(side="left")
        self.est_grupo_var = tk.StringVar(value="Todos")
        self.est_grupo_combo = ttk.Combobox(
            filtros, textvariable=self.est_grupo_var, state="readonly", width=14,
            style="Gym.TCombobox",
        )
        self.est_grupo_combo.pack(side="left", padx=(6, 12))
        self.est_grupo_combo.bind("<<ComboboxSelected>>", self._al_cambiar_grupo_est)

        tk.Label(
            filtros, text="Estiramiento:", font=("Segoe UI", 8), fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left")
        self.est_combo = ttk.Combobox(filtros, state="readonly", style="Gym.TCombobox")
        self.est_combo.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.est_combo.bind("<<ComboboxSelected>>", self._al_seleccionar_est)

        # --- Vista previa ---
        superior = ttk.Frame(contenedor, style="Gym.TFrame")

        panel_desc = ttk.LabelFrame(superior, text="Cómo realizarlo", padding=4)
        panel_desc.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.est_txt = tk.Text(
            panel_desc, width=40, height=8, wrap="word", bg=GRIS_OSCURO, fg=BLANCO,
            relief="flat", padx=6, pady=4, font=("Segoe UI", 9), highlightthickness=0,
        )
        self.est_txt.configure(state="disabled")
        barra_desc = ttk.Scrollbar(panel_desc, orient="vertical", command=self.est_txt.yview)
        self.est_txt.configure(yscrollcommand=barra_desc.set)
        self.est_txt.pack(side="left", fill="both", expand=True)
        barra_desc.pack(side="right", fill="y")

        panel_img = ttk.LabelFrame(superior, text="Ilustración", padding=4)
        panel_img.pack(side="right", fill="both", expand=True)
        self.est_lbl_img = tk.Label(
            panel_img, bg=GRIS_OSCURO, fg=GRIS_TEXTO, font=("Segoe UI", 9), text=""
        )
        self.est_lbl_img.pack(expand=True, fill="both")
        self.est_lbl_fuente = ttk.Label(panel_img, text="", style="Estado.TLabel")
        self.est_lbl_fuente.pack(anchor="w")

        # --- Selección del paciente ---
        marco_pac = ttk.LabelFrame(
            contenedor, text="Estiramientos del paciente", padding=6
        )
        cols = ("nombre", "grupo", "momento", "duracion")
        self.est_tree = ttk.Treeview(
            marco_pac, columns=cols, show="headings", height=3,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("nombre", "Estiramiento", 300, "w"),
            ("grupo", "Grupo", 100, "w"),
            ("momento", "Momento", 190, "w"),
            ("duracion", "Duración", 90, "center"),
        ):
            self.est_tree.heading(col, text=texto, anchor=alineacion)
            self.est_tree.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion,
                stretch=(col == "nombre"),
            )
        barra_pac = ttk.Scrollbar(marco_pac, orient="vertical", command=self.est_tree.yview)
        self.est_tree.configure(yscrollcommand=barra_pac.set)
        self.est_tree.pack(side="left", fill="both", expand=True)
        barra_pac.pack(side="left", fill="y")

        acciones = ttk.Frame(marco_pac, style="Gym.TFrame")
        acciones.pack(side="left", fill="y", padx=(8, 0))
        tk.Button(
            acciones, text="Quitar seleccionado", command=self._quitar_est,
            font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO, relief="flat",
            padx=8, pady=2, cursor="hand2",
        ).pack(fill="x", pady=(0, 4))
        tk.Button(
            acciones, text="Vaciar selección", command=self._vaciar_est,
            font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO, relief="flat",
            padx=8, pady=2, cursor="hand2",
        ).pack(fill="x")
        self.est_lbl_total = ttk.Label(acciones, text="0 estiramientos", style="Estado.TLabel")
        self.est_lbl_total.pack(anchor="w", pady=(8, 0))

        # --- Alta ---
        marco_alta = ttk.LabelFrame(
            contenedor, text="Añadir a la selección del paciente", padding=6
        )
        tk.Label(
            marco_alta, text="Momento:", font=("Segoe UI", 8), fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left")
        self.est_momento_var = tk.StringVar(value=MOMENTOS[0])
        ttk.Combobox(
            marco_alta, textvariable=self.est_momento_var, values=MOMENTOS,
            state="readonly", width=26, style="Gym.TCombobox",
        ).pack(side="left", padx=(6, 12))
        tk.Label(
            marco_alta, text="Duración:", font=("Segoe UI", 8), fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left")
        self.est_duracion_var = tk.StringVar(value=DURACIONES[3])
        ttk.Combobox(
            marco_alta, textvariable=self.est_duracion_var, values=DURACIONES,
            state="readonly", width=12, style="Gym.TCombobox",
        ).pack(side="left", padx=(6, 12))
        tk.Button(
            marco_alta, text="+ AÑADIR ESTIRAMIENTO", command=self._anadir_est,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=3, cursor="hand2",
        ).pack(side="left")

        filtros.pack(fill="x", pady=(0, 6))
        marco_pac.pack(side="bottom", fill="both", pady=(6, 0))
        marco_alta.pack(side="bottom", fill="x", pady=(6, 0))
        superior.pack(fill="both", expand=True)

        self._cargar_grupos_est()

    # ------------------------------------------------------------------
    # Estiramientos: catálogo y selección del paciente
    # ------------------------------------------------------------------
    def _cargar_grupos_est(self):
        try:
            grupos = database.get_estiramientos_grupos()
        except Exception:
            grupos = []
        self.est_grupo_combo["values"] = ["Todos"] + grupos
        self.est_grupo_combo.current(0)
        self._cargar_catalogo_est()

    def _al_cambiar_grupo_est(self, event=None):
        self._cargar_catalogo_est()

    def _cargar_catalogo_est(self):
        grupo = self.est_grupo_var.get()
        try:
            self.est_catalogo = database.get_estiramientos(
                None if grupo.lower().startswith("todos") else grupo
            )
        except Exception:
            self.est_catalogo = []
        opciones = []
        for est in self.est_catalogo:
            numero = est.get("numero")
            prefijo = f"{int(numero):02d}. " if isinstance(numero, int) else ""
            opciones.append(prefijo + (est.get("nombre") or ""))
        self.est_combo["values"] = opciones
        if opciones:
            self.est_combo.current(0)
            self._al_seleccionar_est()
        else:
            self.est_combo.set("")
            self.est_actual = None
            self._mostrar_est({})

    def _al_seleccionar_est(self, event=None):
        idx = self.est_combo.current()
        if idx < 0 or idx >= len(self.est_catalogo):
            return
        self.est_actual = self.est_catalogo[idx]
        self._mostrar_est(self.est_actual)

    def _mostrar_est(self, est):
        partes = []
        for titulo, clave in (
            ("CÓMO REALIZARLO", "descripcion"),
            ("MÚSCULOS ESTIRADOS", "musculos"),
            ("VARIANTES", "variantes"),
            ("OBSERVACIONES", "observaciones"),
            ("ATENCIÓN", "atencion"),
        ):
            valor = (est.get(clave) or "").strip()
            if valor:
                partes.append(f"{titulo}\n{valor}")
        texto = "\n\n".join(partes) or "Selecciona un estiramiento del catálogo."
        self.est_txt.configure(state="normal")
        self.est_txt.delete("1.0", "end")
        self.est_txt.insert("1.0", texto)
        self.est_txt.configure(state="disabled")
        self._cargar_imagen_est(est)

    def _cargar_imagen_est(self, est):
        self.est_lbl_img.configure(image="", text="")
        self.est_lbl_fuente.configure(text="")
        self._est_foto = None
        if Image is None:
            self.est_lbl_img.configure(text="Pillow no está instalado")
            return

        origen = None
        fuente = ""
        blob = est.get("imagen_blob")
        if blob:
            try:
                with Image.open(io.BytesIO(blob)) as imagen:
                    origen = imagen.convert("RGB")
                fuente = f"BD · imagen_blob ({len(blob) / 1024:.0f} KB)"
            except Exception:
                origen = None
        if origen is None:
            nombre = est.get("imagen") or ""
            if nombre:
                for ext in (".png", ".jpg", ".jpeg"):
                    ruta = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "estiramientos_img", nombre + ext,
                    )
                    if os.path.exists(ruta):
                        try:
                            with Image.open(ruta) as imagen:
                                origen = imagen.convert("RGB")
                            fuente = f"archivo · {nombre}{ext}"
                        except Exception:
                            origen = None
                        break
        if origen is None:
            self.est_lbl_img.configure(text="Sin ilustración guardada")
            return

        copia = origen.copy()
        copia.thumbnail((460, 320), Image.LANCZOS)
        self._est_foto = ImageTk.PhotoImage(copia)
        self.est_lbl_img.configure(image=self._est_foto, text="")
        ancho, alto = origen.size
        self.est_lbl_fuente.configure(
            text=f"Imagen desde {fuente} · original {ancho}x{alto} px"
        )

    def _anadir_est(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de añadir."
            )
            return
        est = self.est_actual
        if not est:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un estiramiento del catálogo."
            )
            return
        try:
            database.insert_estiramiento_paciente(
                {
                    "paciente_id": paciente_id,
                    "id_estiramiento": est.get("id_estiramiento"),
                    "grupo": est.get("grupo"),
                    "nombre": est.get("nombre"),
                    "momento": self.est_momento_var.get(),
                    "duracion": self.est_duracion_var.get(),
                    "notas": "",
                }
            )
        except Exception as error:
            messagebox.showerror(
                "Estiramientos", f"No se pudo añadir el estiramiento:\n{error}"
            )
            return
        self._cargar_est_paciente()
        self._mensaje(f"Añadido: {est.get('nombre')}")

    def _quitar_est(self):
        seleccion = self.est_tree.selection()
        if not seleccion:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un estiramiento de la lista."
            )
            return
        try:
            database.delete_estiramiento_paciente(int(seleccion[0]))
        except Exception as error:
            messagebox.showerror(
                "Estiramientos", f"No se pudo quitar:\n{error}"
            )
            return
        self._cargar_est_paciente()
        self._mensaje("Estiramiento quitado de la selección.")

    def _vaciar_est(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None or not getattr(self, "est_seleccion", []):
            return
        if not messagebox.askyesno(
            "Estiramientos", "¿Vaciar todos los estiramientos de este paciente?"
        ):
            return
        try:
            database.delete_estiramientos_paciente(paciente_id)
        except Exception as error:
            messagebox.showerror("Estiramientos", f"No se pudo vaciar:\n{error}")
            return
        self._cargar_est_paciente()
        self._mensaje("Selección de estiramientos vaciada.")

    def _cargar_est_paciente(self):
        if not hasattr(self, "est_tree"):
            return
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self.est_seleccion = []
        else:
            try:
                self.est_seleccion = database.get_estiramientos_paciente(paciente_id)
            except Exception:
                self.est_seleccion = []
        self._render_est_paciente()

    def _render_est_paciente(self):
        for item in self.est_tree.get_children():
            self.est_tree.delete(item)
        for registro in getattr(self, "est_seleccion", []):
            self.est_tree.insert(
                "",
                "end",
                iid=str(registro.get("id_seleccion")),
                values=(
                    registro.get("nombre") or "-",
                    registro.get("grupo") or "-",
                    registro.get("momento") or "-",
                    registro.get("duracion") or "-",
                ),
            )
        total = len(getattr(self, "est_seleccion", []))
        self.est_lbl_total.configure(
            text=f"{total} estiramiento" + ("" if total == 1 else "s")
        )

    # ------------------------------------------------------------------
    # Rutina del paciente (alta, listado y borrado)
    # ------------------------------------------------------------------
    def _mensaje(self, texto):
        """Muestra una confirmación breve en la barra de estado."""
        base = getattr(self, "_estado_base", "") or "Rutinas"
        self.lbl_estado.configure(text=f"{base}  ·  {texto}")

    def _paciente_actual(self):
        if self.paciente_id is not None:
            return self.paciente_id
        return getattr(self.app, "id_paciente_antro", None)

    def _anadir_ejercicio(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de añadir ejercicios."
            )
            return
        ej = self.ejercicio_seleccionado
        if not ej:
            messagebox.showwarning("Rutinas", "Selecciona un ejercicio de la lista.")
            return

        series = self.reg_entradas["Series"].get().strip()
        repeticiones = self.reg_entradas["Repeticiones"].get().strip()
        if not series and not repeticiones:
            messagebox.showwarning(
                "Rutinas", "Indica al menos las series o las repeticiones."
            )
            return

        datos = {
            "paciente_id": paciente_id,
            "grupo": ej.get("grupo") or self.grupo,
            "num": ej.get("num"),
            "nombre": ej.get("nombre"),
            "equipo": ej.get("equipo"),
            "series": series,
            "repeticiones": repeticiones,
            "descanso_rep": self.reg_entradas["Descanso entre repeticiones (seg)"].get().strip(),
            "descanso_series": self.reg_entradas["Descanso entre series (seg)"].get().strip(),
            "peso": self.reg_entradas["Peso (kg)"].get().strip(),
        }
        try:
            database.insert_rutina_paciente(datos)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo añadir el ejercicio:\n{error}"
            )
            return

        self.reg_entradas["Peso (kg)"].delete(0, "end")
        self._cargar_rutina()
        self._mensaje(f"Añadido: {datos['nombre']}")

    def _quitar_ejercicio(self):
        seleccion = self.tree_rutina.selection()
        if not seleccion:
            messagebox.showwarning(
                "Rutinas", "Selecciona un ejercicio de la rutina del paciente."
            )
            return
        try:
            database.delete_rutina_paciente(int(seleccion[0]))
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo quitar el ejercicio:\n{error}"
            )
            return
        self._cargar_rutina()
        self._mensaje("Ejercicio quitado de la rutina.")

    def _vaciar_rutina(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None or not getattr(self, "rutina", []):
            return
        if not messagebox.askyesno(
            "Rutinas", "¿Vaciar toda la rutina de este paciente?"
        ):
            return
        try:
            database.delete_rutinas_paciente(paciente_id)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo vaciar la rutina:\n{error}"
            )
            return
        self._cargar_rutina()
        self._mensaje("Rutina vaciada.")

    def _cargar_rutina(self):
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            self.rutina = []
        else:
            try:
                self.rutina = database.get_rutinas_paciente(paciente_id)
            except Exception:
                self.rutina = []
        self._render_rutina()

    def _render_rutina(self):
        if not hasattr(self, "tree_rutina"):
            return
        for item in self.tree_rutina.get_children():
            self.tree_rutina.delete(item)
        for posicion, registro in enumerate(getattr(self, "rutina", []), start=1):
            self.tree_rutina.insert(
                "",
                "end",
                iid=str(registro["id_rutina"]),
                values=(
                    posicion,
                    registro["nombre"],
                    registro["equipo"] or "-",
                    registro["series"] or "-",
                    registro["repeticiones"] or "-",
                    registro["descanso_rep"] or "-",
                    registro["descanso_series"] or "-",
                    registro["peso"] or "-",
                ),
            )
        total = len(getattr(self, "rutina", []))
        self.lbl_rutina_total.configure(
            text=f"{total} ejercicio" + ("" if total == 1 else "s")
        )

    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        if paciente_id is None:
            self._estado_base = "Rutinas: sin paciente seleccionado"
            self.lbl_estado.configure(text=self._estado_base)
        else:
            nombre = ""
            try:
                paciente = database.obtener_paciente(paciente_id)
                nombre = (paciente or {}).get("nombre") or ""
            except Exception:
                nombre = ""
            if nombre:
                texto = f"Rutina de {nombre} (ID {paciente_id})"
            else:
                texto = f"Rutina del paciente {paciente_id}"
            self._estado_base = texto
            self.lbl_estado.configure(text=texto)
        self._cargar_rutina()
        self._cargar_est_paciente()

    def refrescar_estado(self):
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id != self.paciente_id:
            self.cargar(paciente_id)
            return
        # Mismo paciente: refresca la selección de estiramientos por si cambió
        # desde la pestaña Estiramientos.
        self._cargar_est_paciente()
