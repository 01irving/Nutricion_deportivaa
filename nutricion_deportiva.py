import json
import math
import os
import tkinter as tk
from tkinter import messagebox, ttk

import database
import smae_loader
from r24h_tab import R24hTab
from formulas_tab import FormulasTab
from equivalentes_tab import EquivalesTab
from menu_tab import MenusTab
from suplementos_tab import SuplementosTab
from estiramientos_tab import EstiramientosTab
from antecedentes_tab import AntecedentesTab
from componentes5_tab import Componentes5Tab
from rutinas_tab import RutinasTab

ETIQUETAS = [
    ("deporte", "Deporte"),
    ("fecha", "Fecha"),
    ("nombre", "Nombre"),
    ("dob", "DOB"),
    ("fecha_nacimiento", "Fecha de nacimiento"),
    ("direccion", "Dirección"),
    ("genero", "Género"),
    ("telefono", "Teléfono"),
    ("email", "Email"),
    ("facebook", "Facebook"),
    ("gimnasio", "Gimnasio"),
    ("coach", "Coach"),
    ("proposito", "Propósito"),
]

ETIQUETAS_ANTROPOMETRIA = [
    ("fecha", "Fecha"),
    ("peso", "Peso"),
    ("altura", "Altura"),
    ("sum_pliegues", "Sum 7-8 pliegues"),
    ("grasa", "% Grasa"),
    ("metodo", "Método"),
    ("clasificacion_peso", "Clasificación peso"),
    ("masa_muscular", "% Masa muscular"),
    ("problemas_soluciones", "Problemas y soluciones"),
]

ISAK_ENCABEZADO = [
    ("evaluador", "Nombre del evaluador"),
    ("id_paciente", "ID del paciente"),
    ("hora", "Hora (HH:MM)"),
    ("fecha_eval", "Fecha (dd/mm/aaaa)"),
    ("comentarios", "Comentarios"),
]

ISAK_ESTRUCTURA = [
    (
        "Básicos",
        [
            ("masa_corporal", "Masa Corporal"),
            ("estatura", "Estatura"),
            ("talla_sentado", "Talla sentado"),
            ("envergadura", "Envergadura"),
        ],
    ),
    (
        "Panículos",
        [
            ("triceps", "Tríceps"),
            ("subescapular", "Subescapular"),
            ("biceps", "Bíceps"),
            ("cresta_iliaca", "Cresta Ilíaca"),
            ("supraespinal", "Supraespinal"),
            ("abdominal", "Abdominal"),
            ("muslo_anterior", "Muslo anterior"),
            ("pierna_medial", "Pierna medial"),
        ],
    ),
    (
        "Circunferencias",
        [
            ("cabeza", "Cabeza"),
            ("cuello", "Cuello"),
            ("brazo_relajado", "Brazo relajado"),
            ("brazo_flexionado", "Brazo flex. & en contracción"),
            ("antebrazo", "Antebrazo (máximo)"),
            ("muneca", "Muñeca (estiloideo distal)"),
            ("torax_mesoesternal", "Tórax (mesoesternal)"),
            ("cintura", "Cintura (mínima)"),
            ("caderas", "Caderas (máxima)"),
            ("muslo_1cm_gluteo", "Muslo (1 cm glúteo)"),
            ("muslo_medio", "Muslo medio"),
            ("pierna_maximo", "Pierna (máximo)"),
            ("tobillo", "Tobillo (mínimo)"),
        ],
    ),
    (
        "Longitudes",
        [
            ("acromiale_radiale", "Acromiale-radiale"),
            ("radiale_stylion", "Radiale-stylion"),
            ("midstylion_dactylion", "Midstylion-dactylion"),
            ("altura_ilioespinal", "Altura ilioespinal"),
            ("altura_trocanterea", "Altura trocantérea"),
            ("trochanterion_tibiale", "Trochanterion-tibiale laterale"),
            ("altura_tibial_lateral", "Altura tibial lateral"),
            ("tibiale_medial_sphyrion", "Tibiale mediale-sphyrion tibiale"),
        ],
    ),
    (
        "Diámetros",
        [
            ("biacromial", "Biacromial"),
            ("abdominal_ap_sagital", "Abdominal A-P (sagital)"),
            ("biiliocrestal", "Biiliocrestal"),
            ("longitud_pie", "Longitud de pié"),
            ("torax_transverso", "Tórax transverso"),
            ("torax_ap", "Tórax A-P"),
            ("humero", "Húmero"),
            ("biestiloideo", "Biestiloideo"),
            ("femur", "Fémur"),
        ],
    ),
]


SOMATOTIPO_CAMPOS = [
    ("peso", "Peso (kg)"),
    ("estatura", "Estatura (cm)"),
    ("triceps", "Tríceps (mm)"),
    ("subescapular", "Subescapular (mm)"),
    ("supraespinal", "Supraespinal (mm)"),
    ("pierna_medial", "Pierna medial (mm)"),
    ("humero", "Húmero (cm)"),
    ("femur", "Fémur (cm)"),
    ("brazo_flexionado", "Brazo flex. tensado (cm)"),
    ("pierna_maximo", "Pierna máximo (cm)"),
]

SOMATOTIPO_ISAK = {
    "peso": "masa_corporal",
    "estatura": "estatura",
    "triceps": "triceps",
    "subescapular": "subescapular",
    "supraespinal": "supraespinal",
    "pierna_medial": "pierna_medial",
    "humero": "humero",
    "femur": "femur",
    "brazo_flexionado": "brazo_flexionado",
    "pierna_maximo": "pierna_maximo",
}

ISAK_PLIEGUES = {
    "triceps",
    "subescapular",
    "supraespinal",
    "pierna_medial",
}
ISAK_TOLERANCIA_PLIEGUES = 0.05
ISAK_TOLERANCIA_OTROS = 0.01


NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"


class DialogoAccion(tk.Toplevel):
    def __init__(self, parent, paciente):
        super().__init__(parent)
        self.title("Paciente seleccionado")
        self.configure(bg=NEGRO)
        self.geometry("380x180")
        self.transient(parent)
        self.grab_set()

        self.accion = None

        etiqueta = (
            f"{paciente.get('codigo') or ''} — {paciente.get('nombre') or ''}"
        )
        ttk.Label(
            self, text=etiqueta, style="Estado.TLabel"
        ).pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(
            self,
            text="¿Qué deseas hacer con este paciente?",
            style="Gym.TLabel",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        barra = ttk.Frame(self, style="Gym.TFrame")
        barra.pack(fill="x", padx=16)

        def boton(texto, accion, primario):
            return tk.Button(
                barra,
                text=texto,
                command=lambda: self._elegir(accion),
                font=("Impact", 12),
                fg=NEGRO if primario else NEON,
                bg=NEON if primario else GRIS,
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=14,
                pady=6,
                cursor="hand2",
            )

        boton("EDICIÓN", "edicion", True).pack(side="left")
        boton("SEGUIMIENTO", "seguimiento", False).pack(side="left", padx=8)
        boton("CANCELAR", None, False).pack(side="left")

    def _elegir(self, accion):
        self.accion = accion
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nutrición Deportiva")
        ancho_ventana = 960
        alto_trabajo = self.winfo_screenheight()
        try:  # alto util de Windows, descontando la barra de tareas
            import ctypes
            from ctypes import wintypes

            area = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0):
                alto_trabajo = area.bottom - area.top
        except Exception:
            pass
        alto_ventana = min(800, alto_trabajo - 46)
        x = max(0, (self.winfo_screenwidth() - ancho_ventana) // 2)
        y = 20 if alto_ventana >= 800 else 0
        self.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
        self.minsize(880, 600)
        self.configure(bg=NEGRO)

        self.configurar_tema()

        database.init_db()
        self._cargar_smae()

        self.id_paciente = None
        self.id_paciente_antro = None

        self._logo_membrete = None
        self._crear_membrete()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(6, 8))

        self.entries = {}
        self.entries_antro = {}

        marco_paciente = self.crear_formulario(
            self.notebook,
            "  💪 Paciente  ",
            ETIQUETAS,
            [
                ("NUEVO PACIENTE", self.nuevo_paciente),
                ("GUARDAR PACIENTE", self.guardar),
            ],
            self.entries,
        )

        self.lbl_estado = ttk.Label(
            marco_paciente,
            text="Nuevo paciente (sin guardar)",
            style="Estado.TLabel",
        )
        self.lbl_estado.grid(
            row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6)
        )

        ttk.Label(
            marco_paciente,
            text="PACIENTES GUARDADOS",
            style="Estado.TLabel",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))

        contenedor_tabla = ttk.Frame(marco_paciente, style="Gym.TFrame")
        contenedor_tabla.grid(
            row=5, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 6)
        )
        self.tabla_pacientes = ttk.Treeview(
            contenedor_tabla,
            columns=("codigo", "nombre", "deporte", "gimnasio", "fecha"),
            show="headings",
            style="Gym.Treeview",
            height=5,
        )
        for col, encabezado, ancho in (
            ("codigo", "Código", 90),
            ("nombre", "Nombre", 200),
            ("deporte", "Deporte", 140),
            ("gimnasio", "Gimnasio", 140),
            ("fecha", "Fecha", 100),
        ):
            self.tabla_pacientes.heading(col, text=encabezado)
            self.tabla_pacientes.column(col, width=ancho, anchor="w")

        scroll_pac = ttk.Scrollbar(
            contenedor_tabla,
            orient="vertical",
            command=self.tabla_pacientes.yview,
        )
        self.tabla_pacientes.configure(yscrollcommand=scroll_pac.set)
        self.tabla_pacientes.pack(side="left", fill="both", expand=True)
        scroll_pac.pack(side="right", fill="y")
        self.tabla_pacientes.bind(
            "<Double-1>", self._seleccionar_de_tabla
        )

        tk.Button(
            marco_paciente,
            text="ABRIR SELECCIONADO",
            command=self._seleccionar_de_tabla,
            font=("Impact", 12),
            fg=NEON,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 10))

        marco_paciente.rowconfigure(5, weight=1)
        self.refrescar_tabla_pacientes()

        # La pestaña Antecedentes va inmediatamente después de Paciente.
        self.tab_antecedentes = AntecedentesTab(self)
        self.tab_antecedentes.create(self.notebook)

        marco_antro = self.crear_formulario(
            self.notebook,
            "  📏 Antropometría  ",
            ETIQUETAS_ANTROPOMETRIA,
            [("GUARDAR ANTROPOMETRÍA", self.guardar_antro)],
            self.entries_antro,
        )
        self.marco_antro = marco_antro

        self.lbl_antro = ttk.Label(
            marco_antro,
            text="Seguimiento: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_antro.grid(
            row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6)
        )

        self.entries_isak = {}
        self._crear_panel_isak(marco_antro)

        self._crear_tab_somatotipo()

        self.tab_componentes = Componentes5Tab(self)
        self.tab_componentes.create(self.notebook)

        self.tab_r24h = R24hTab(self)
        self.tab_r24h.create(self.notebook)

        self.tab_formulas = FormulasTab(self)
        self.tab_formulas.create(self.notebook)

        self.tab_equivalentes = EquivalesTab(self)
        self.tab_equivalentes.create(self.notebook)

        self.tab_menus = MenusTab(self)
        self.tab_menus.create(self.notebook)
        self.tab_rutinas = RutinasTab(self)
        self.tab_rutinas.create(self.notebook)

        self.tab_suplementos = SuplementosTab(self)
        self.tab_suplementos.create(self.notebook)

        self.tab_estiramientos = EstiramientosTab(self)
        self.tab_estiramientos.create(self.notebook)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._configurar_autocompletado()

    def _on_tab_changed(self, event=None):
        seleccionado = self.notebook.select()
        if seleccionado == str(self.tab_equivalentes.marco_canvas):
            self.tab_equivalentes.tomar_de_formulas(silencioso=True)
        if seleccionado == str(self.tab_menus.marco):
            self.tab_menus.sincronizar_distribucion()
        if seleccionado == str(self.tab_suplementos.marco):
            self.tab_suplementos.refrescar_estado()
        if seleccionado == str(self.tab_estiramientos.marco):
            self.tab_estiramientos.refrescar_estado()
        if seleccionado == str(self.tab_componentes.marco):
            self.tab_componentes.refrescar_estado()
        if hasattr(self, "tab_rutinas") and hasattr(self.tab_rutinas, "refrescar_estado"):
            self.tab_rutinas.refrescar_estado()

    def _cargar_smae(self):
        if database.contar_smae_alimentos() > 0:
            return
        try:
            smae_loader.importar_smae()
        except Exception as error:
            messagebox.showwarning(
                "SMAE",
                "No se pudo importar SMAE-5.xlsx:\n" f"{error}",
            )

    def crear_formulario(
        self, notebook, titulo_tab, campos, botones, destino
    ):
        marco_tab = ttk.Frame(notebook, style="Gym.TFrame")
        notebook.add(marco_tab, text=titulo_tab)

        titulo = tk.Label(
            marco_tab,
            text="NUTRICIÓN DEPORTIVA",
            font=("Impact", 20),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        titulo.grid(row=0, column=0, columnspan=2, sticky="we", pady=(4, 10))
        marco_tab.columnconfigure(0, weight=1, uniform="col")
        marco_tab.columnconfigure(1, weight=1, uniform="col")

        mitad = (len(campos) + 1) // 2
        grupos = [campos[:mitad], campos[mitad:]]

        for c, grupo in enumerate(grupos):
            marco = ttk.Frame(marco_tab, style="Gym.TFrame")
            marco.grid(row=1, column=c, sticky="nw", padx=(4, 0), pady=4)
            for fila, (clave, etiqueta) in enumerate(grupo):
                ttk.Label(
                    marco, text=f"{etiqueta}:", style="Gym.TLabel"
                ).grid(row=fila, column=0, sticky="e", padx=(4, 4), pady=6)
                entry = ttk.Entry(marco, width=28, style="Gym.TEntry")
                entry.grid(row=fila, column=1, sticky="w", padx=(0, 8), pady=6)
                destino[clave] = entry

        barra = ttk.Frame(marco_tab, style="Gym.TFrame")
        barra.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=16)

        for i, (texto, comando) in enumerate(botones):
            primario = i == 0
            tk.Button(
                barra,
                text=texto,
                command=comando,
                font=("Impact", 12),
                fg=NEGRO if primario else NEON,
                bg=NEON if primario else GRIS,
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=16,
                pady=6,
                cursor="hand2",
            ).pack(side="left", padx=(0, 8))

        return marco_tab

    def _crear_membrete(self):
        """Encabezado de la ventana: el mismo membrete de las impresiones."""
        try:
            from impresion_utils import DATOS_PROFESIONAL, RUTA_LOGO

            datos = dict(DATOS_PROFESIONAL)
            ruta_logo = RUTA_LOGO
        except Exception:
            datos = {
                "nombre": "Irving Gualberto Euan Dzul",
                "direccion": "Calle 21 Num 42. Nunkiní, Calkiní, Camp.",
                "telefono": "9961059072",
                "redes_sociales": "facebook: Irving Euan",
            }
            ruta_logo = ""

        marco = tk.Frame(self, bg=GRIS_OSCURO)
        marco.pack(fill="x", padx=10, pady=(4, 0))

        if ruta_logo and os.path.exists(ruta_logo):
            try:
                from PIL import Image, ImageTk

                with Image.open(ruta_logo) as imagen:
                    original = imagen.convert("RGBA")
                alto = 32
                ancho = max(1, int(original.width * alto / original.height))
                copia = original.resize((ancho, alto), Image.LANCZOS)
                self._logo_membrete = ImageTk.PhotoImage(copia)
                tk.Label(
                    marco, image=self._logo_membrete, bg=GRIS_OSCURO, bd=0
                ).pack(side="left", padx=(8, 10), pady=3)
            except Exception:
                self._logo_membrete = None

        tk.Label(
            marco,
            text=datos.get("nombre", ""),
            font=("Impact", 13),
            fg=BLANCO,
            bg=GRIS_OSCURO,
        ).pack(side="left", pady=3)

        contacto = "  ·  ".join(
            str(datos[clave])
            for clave in ("direccion", "telefono", "redes_sociales")
            if datos.get(clave)
        )
        tk.Label(
            marco,
            text=contacto,
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(side="left", padx=10, pady=3)

        tk.Label(
            marco,
            text="NUTRICIÓN DEPORTIVA",
            font=("Impact", 11),
            fg=NEON,
            bg=GRIS_OSCURO,
        ).pack(side="right", padx=10, pady=3)

        tk.Frame(self, bg=NARANJA, height=2).pack(fill="x", padx=10, pady=(2, 0))

    def configurar_tema(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=GRIS_OSCURO, foreground=BLANCO)
        style.configure("Gym.TFrame", background=GRIS_OSCURO)
        style.configure(
            "Gym.TLabel",
            background=GRIS_OSCURO,
            foreground=BLANCO,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Estado.TLabel",
            background=GRIS_OSCURO,
            foreground=NEON,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Gym.TEntry",
            fieldbackground=GRIS,
            foreground=BLANCO,
            insertcolor=NEON,
            padding=4,
        )
        style.map(
            "Gym.TEntry",
            fieldbackground=[("focus", "#3A3A3A")],
            bordercolor=[("focus", NEON)],
        )
        style.configure(
            "Gym.TCombobox",
            fieldbackground=GRIS,
            background=GRIS,
            foreground=BLANCO,
            arrowcolor=NEON,
            padding=4,
        )
        style.map(
            "Gym.TCombobox",
            fieldbackground=[("readonly", GRIS), ("focus", "#3A3A3A")],
            foreground=[("readonly", BLANCO)],
            background=[("readonly", GRIS)],
            arrowcolor=[("readonly", NEON)],
        )
        style.configure(
            "Gym.TSpinbox",
            fieldbackground=GRIS,
            background=GRIS,
            foreground=BLANCO,
            arrowcolor=NEON,
            insertcolor=NEON,
            padding=4,
        )
        style.map(
            "Gym.TSpinbox",
            fieldbackground=[("focus", "#3A3A3A")],
            background=[("active", NARANJA)],
            bordercolor=[("focus", NEON)],
        )
        style.configure(
            "TNotebook",
            background=NEGRO,
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=GRIS,
            foreground=GRIS_TEXTO,
            padding=(16, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", NEON)],
            foreground=[("selected", NEGRO)],
        )
        style.configure(
            "Gym.Treeview",
            background=GRIS,
            fieldbackground=GRIS,
            foreground=BLANCO,
            rowheight=24,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Eq.Treeview",
            background=GRIS,
            fieldbackground=GRIS,
            foreground=BLANCO,
            rowheight=30,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Eq.Treeview.Heading",
            background=NEON,
            foreground=NEGRO,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Eq.Treeview",
            background=[("selected", NARANJA)],
            foreground=[("selected", BLANCO)],
        )
        style.configure(
            "Gym.Treeview.Heading",
            background=NEON,
            foreground=NEGRO,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Gym.Treeview",
            background=[("selected", NARANJA)],
            foreground=[("selected", BLANCO)],
        )

    def _leer(self, destino):
        return {clave: entry.get().strip() for clave, entry in destino.items()}

    def _limpiar(self, destino):
        for entry in destino.values():
            entry.delete(0, "end")

    def nuevo_paciente(self):
        self._limpiar(self.entries)
        self.id_paciente = None
        self.id_paciente_antro = None
        self._reset_tabs()
        self.lbl_antro.configure(text="Antropometría: sin paciente")
        self.lbl_soma.configure(text="Somatotipo: sin paciente")
        self.lbl_estado.configure(text="Nuevo paciente (sin guardar)")
        self.entries["nombre"].focus_set()

    def _reset_tabs(self):
        """Limpia el estado ligado al paciente en todas las pestañas."""
        for tab in (
            getattr(self, "tab_r24h", None),
            getattr(self, "tab_formulas", None),
            getattr(self, "tab_equivalentes", None),
            getattr(self, "tab_menus", None),
            getattr(self, "tab_suplementos", None),
            getattr(self, "tab_estiramientos", None),
            getattr(self, "tab_antecedentes", None),
            getattr(self, "tab_componentes", None),
        ):
            if tab is None:
                continue
            metodo = getattr(tab, "desvincular", None) or getattr(
                tab, "limpiar", None
            )
            if callable(metodo):
                try:
                    metodo()
                except Exception:
                    pass

    def refrescar_tabla_pacientes(self):
        for fila in self.tabla_pacientes.get_children():
            self.tabla_pacientes.delete(fila)
        for paciente in database.obtener_pacientes():
            self.tabla_pacientes.insert(
                "",
                "end",
                iid=str(paciente["id"]),
                values=(
                    paciente.get("codigo") or "",
                    paciente.get("nombre") or "",
                    paciente.get("deporte") or "",
                    paciente.get("gimnasio") or "",
                    paciente.get("fecha") or "",
                ),
            )

    def _seleccionar_de_tabla(self, event=None):
        seleccion = self.tabla_pacientes.selection()
        if not seleccion:
            messagebox.showinfo(
                "Selección", "Selecciona un paciente de la lista."
            )
            return
        self._seleccionar_paciente(int(seleccion[0]))

    def _configurar_autocompletado(self):
        self._sugerencias = []
        self.lista_popup = tk.Listbox(
            self,
            bg=GRIS,
            fg=BLANCO,
            selectbackground=NARANJA,
            selectforeground=BLANCO,
            activestyle="none",
            highlightthickness=1,
            highlightbackground=NEON,
            font=("Segoe UI", 10),
            takefocus=0,
            borderwidth=0,
        )
        self.lista_popup.bind("<Button-1>", self._clic_sugerencia)
        self.lista_popup.bind("<Return>", self._clic_sugerencia)

        entry = self.entries["nombre"]
        entry.bind("<KeyRelease>", self._al_escribir)
        entry.bind("<Down>", self._bajar_a_lista)
        entry.bind("<Escape>", lambda _e: self._ocultar_popup())
        entry.bind("<FocusOut>", lambda _e: self.after(150, self._ocultar_si_fuera))

    def _al_escribir(self, event=None):
        if event is not None and event.keysym in (
            "Down",
            "Up",
            "Return",
            "Escape",
            "Tab",
            "Left",
            "Right",
        ):
            return
        texto = self.entries["nombre"].get().strip().lower()
        if not texto:
            self._ocultar_popup()
            return
        pacientes = database.obtener_pacientes()
        coincidencias = [
            p
            for p in pacientes
            if texto in (p.get("nombre") or "").lower()
            or texto in (p.get("codigo") or "").lower()
        ][:8]
        self._sugerencias = coincidencias
        if not coincidencias:
            self._ocultar_popup()
            return
        self.lista_popup.delete(0, "end")
        for p in coincidencias:
            self.lista_popup.insert(
                "end", f"{p.get('codigo') or ''}   {p.get('nombre') or ''}"
            )
        self._mostrar_popup()

    def _mostrar_popup(self):
        entry = self.entries["nombre"]
        self.update_idletasks()
        x = entry.winfo_rootx() - self.winfo_rootx()
        y = entry.winfo_rooty() - self.winfo_rooty() + entry.winfo_height()
        alto = min(len(self._sugerencias) * 22 + 4, 190)
        self.lista_popup.place(
            x=x, y=y, width=max(entry.winfo_width(), 220), height=alto
        )
        self.lista_popup.lift()

    def _ocultar_popup(self):
        self.lista_popup.place_forget()

    def _ocultar_si_fuera(self):
        if self.focus_get() is not self.lista_popup:
            self._ocultar_popup()

    def _bajar_a_lista(self, event=None):
        if self.lista_popup.winfo_ismapped() and self.lista_popup.size():
            self.lista_popup.focus_set()
            self.lista_popup.selection_clear(0, "end")
            self.lista_popup.selection_set(0)
            self.lista_popup.activate(0)

    def _clic_sugerencia(self, event=None):
        if not self._sugerencias:
            return
        if event is not None and hasattr(event, "y"):
            indice = self.lista_popup.nearest(event.y)
        else:
            seleccion = self.lista_popup.curselection()
            if not seleccion:
                return
            indice = seleccion[0]
        paciente = self._sugerencias[indice]
        self._ocultar_popup()
        self.entries["nombre"].delete(0, "end")
        self.entries["nombre"].insert(0, paciente.get("nombre") or "")
        self._seleccionar_paciente(paciente["id"])

    def _seleccionar_paciente(self, id_paciente):
        paciente = database.obtener_paciente(id_paciente)
        if not paciente:
            return
        dialogo = DialogoAccion(self, paciente)
        self.wait_window(dialogo)
        if dialogo.accion == "edicion":
            self._cargar_para_edicion(paciente)
        elif dialogo.accion == "seguimiento":
            self._iniciar_seguimiento(paciente)

    def _cargar_para_edicion(self, paciente):
        for clave, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, paciente.get(clave, "") or "")
        self.id_paciente = paciente["id"]
        self.lbl_estado.configure(
            text=f"Editando {paciente.get('codigo') or ''} — "
            f"{paciente.get('nombre', '')}"
        )
        self._asignar_paciente_activo(paciente, "edicion")
        self.limpiar_somatotipo()
        if self.cargar_somatotipo_isak(silencioso=True):
            self.calcular_somatotipo(silencioso=True)

    def _asignar_paciente_activo(self, paciente, modo):
        self.id_paciente_antro = paciente["id"]
        prefijo = "Editando" if modo == "edicion" else "Seguimiento de"
        etiqueta = (
            f"{prefijo} {paciente.get('codigo') or ''} — "
            f"{paciente.get('nombre', '')}"
        )
        self.lbl_antro.configure(text=etiqueta)
        self.lbl_soma.configure(text=etiqueta)
        entry_id = self.entries_isak.get("id_paciente")
        if entry_id is not None:
            entry_id.state(["!readonly"])
            entry_id.delete(0, "end")
            entry_id.insert(0, paciente.get("codigo") or "")
            entry_id.state(["readonly"])
        self.tab_r24h.cargar(paciente["id"], paciente)
        self.tab_equivalentes.cargar(paciente["id"])
        self.tab_menus.cargar(paciente["id"])
        self.tab_suplementos.cargar(paciente["id"])
        self.tab_estiramientos.cargar(paciente["id"])
        self.tab_antecedentes.cargar(paciente["id"])
        self.tab_componentes.cargar(paciente["id"])
        return etiqueta

    def _iniciar_seguimiento(self, paciente):
        self._asignar_paciente_activo(paciente, "seguimiento")
        self.notebook.select(self.marco_antro)
        self.entries_antro["fecha"].focus_set()
        self.limpiar_somatotipo()
        if self.cargar_somatotipo_isak(silencioso=True):
            self.calcular_somatotipo(silencioso=True)

    def guardar(self):
        datos = self._leer(self.entries)
        if not datos["nombre"]:
            messagebox.showwarning("Validación", "El nombre es obligatorio.")
            return
        try:
            nuevo = self.id_paciente is None
            if nuevo:
                self.id_paciente = database.guardar_paciente(datos)
                registro = database.obtener_paciente(self.id_paciente)
                accion = (
                    f"Paciente '{datos['nombre']}' guardado con código "
                    f"{registro['codigo']}."
                )
            else:
                database.actualizar_paciente(self.id_paciente, datos)
                registro = database.obtener_paciente(self.id_paciente)
                accion = (
                    f"Paciente {registro['codigo']} actualizado "
                    f"('{datos['nombre']}')."
                )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar:\n{exc}")
            return
        self.lbl_estado.configure(
            text=f"Editando {registro['codigo']} — {datos['nombre']}"
        )
        self.refrescar_tabla_pacientes()
        if nuevo:
            # El paciente recién creado queda activo en todas las pestañas
            self._asignar_paciente_activo(registro, "edicion")
        messagebox.showinfo("Guardado", accion)

    def guardar_antro(self):
        datos = self._leer(self.entries_antro)
        if not datos["fecha"]:
            messagebox.showwarning("Validación", "La fecha es obligatoria.")
            return
        if self.id_paciente_antro is None:
            messagebox.showwarning(
                "Seguimiento",
                "Selecciona un paciente (campo Nombre) para el seguimiento.",
            )
            return
        try:
            id_registro = database.guardar_antropometria(
                datos, paciente_id=self.id_paciente_antro
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar:\n{exc}")
            return
        messagebox.showinfo(
            "Guardado", f"Antropometría guardada (ID {id_registro})."
        )
        self._limpiar(self.entries_antro)

    def _crear_panel_isak(self, marco_antro):
        contenedor = ttk.Frame(marco_antro, style="Gym.TFrame")
        contenedor.grid(
            row=4, column=0, columnspan=2, sticky="nsew", padx=8, pady=(4, 4)
        )
        marco_antro.rowconfigure(4, weight=1)

        ttk.Label(
            contenedor,
            text="PERFIL COMPLETO ISAK",
            style="Estado.TLabel",
        ).pack(anchor="w", pady=(2, 4))

        canvas = tk.Canvas(
            contenedor, bg=GRIS_OSCURO, highlightthickness=0, height=260
        )
        scroll = ttk.Scrollbar(
            contenedor, orient="vertical", command=canvas.yview
        )
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        interior = ttk.Frame(canvas, style="Gym.TFrame")
        canvas.create_window((0, 0), window=interior, anchor="nw")
        interior.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"),
        )

        ttk.Label(
            interior, text="Medición", style="Gym.TLabel"
        ).grid(row=0, column=2, padx=(4, 4))
        for i in range(1, 4):
            ttk.Label(
                interior, text=str(i), style="Gym.TLabel"
            ).grid(row=0, column=2 + i, padx=2)

        fila = [1]

        ttk.Label(
            interior, text="Datos de la evaluación", style="Estado.TLabel"
        ).grid(row=fila[0], column=0, columnspan=5, sticky="w", pady=(2, 2))
        fila[0] += 1
        for clave, etiqueta in ISAK_ENCABEZADO:
            r = fila[0]
            fila[0] += 1
            ttk.Label(
                interior, text=f"{etiqueta}:", style="Gym.TLabel"
            ).grid(row=r, column=0, columnspan=2, sticky="w", padx=(4, 8), pady=3)
            entry = ttk.Entry(interior, width=28, style="Gym.TEntry")
            if clave == "id_paciente":
                entry.state(["readonly"])
            entry.grid(
                row=r, column=2, columnspan=3, sticky="w", padx=2, pady=3
            )
            self.entries_isak[clave] = entry

        numero = 0
        for seccion, items in ISAK_ESTRUCTURA:
            ttk.Label(
                interior, text=seccion, style="Estado.TLabel"
            ).grid(row=fila[0], column=0, columnspan=5, sticky="w", pady=(6, 2))
            fila[0] += 1
            for clave, etiqueta in items:
                numero += 1
                r = fila[0]
                fila[0] += 1
                ttk.Label(
                    interior,
                    text=f"{numero}. {etiqueta}",
                    style="Gym.TLabel",
                ).grid(
                    row=r, column=0, columnspan=2, sticky="w", padx=(4, 8), pady=3
                )
                for i in range(1, 4):
                    entry = ttk.Entry(
                        interior, width=8, style="Gym.TEntry"
                    )
                    entry.grid(row=r, column=2 + i, padx=2, pady=3)
                    self.entries_isak[f"{clave}_{i}"] = entry

        tk.Button(
            marco_antro,
            text="GUARDAR PERFIL ISAK",
            command=self.guardar_isak,
            font=("Impact", 12),
            fg=NEON,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 10))

    def guardar_isak(self):
        if self.id_paciente_antro is None:
            messagebox.showwarning(
                "Seguimiento",
                "Selecciona un paciente (campo Nombre) para el seguimiento.",
            )
            return
        datos = {
            clave: entry.get().strip()
            for clave, entry in self.entries_isak.items()
        }
        try:
            id_registro = database.guardar_perfil_isak(
                self.id_paciente_antro, datos
            )
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar:\n{exc}")
            return
        messagebox.showinfo(
            "Guardado", f"Perfil ISAK guardado (ID {id_registro})."
        )
        for clave, entry in self.entries_isak.items():
            if clave == "id_paciente":
                continue
            entry.delete(0, "end")
        if self.cargar_somatotipo_isak(silencioso=True):
            self.calcular_somatotipo(silencioso=True)

    def _crear_tab_somatotipo(self):
        marco = ttk.Frame(self.notebook, style="Gym.TFrame")
        self.notebook.add(marco, text="  🔺 Somatotipo  ")
        self.marco_somatotipo = marco

        titulo = tk.Label(
            marco,
            text="SOMATOTIPO HEATH-CARTER",
            font=("Impact", 20),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        titulo.grid(row=0, column=0, columnspan=2, sticky="we", pady=(4, 4))

        self.lbl_soma = ttk.Label(
            marco,
            text="Seguimiento: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_soma.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 2)
        )

        panel_izq = ttk.Frame(marco, style="Gym.TFrame")
        panel_izq.grid(row=2, column=0, sticky="nw", padx=(8, 4), pady=4)

        ttk.Label(
            panel_izq,
            text="MEDIDAS (regla ISAK: 1 = tal cual | 2 = promedio | 3 = mediana)",
            style="Estado.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.entries_soma = {}
        mitad = (len(SOMATOTIPO_CAMPOS) + 1) // 2
        grupos = [SOMATOTIPO_CAMPOS[:mitad], SOMATOTIPO_CAMPOS[mitad:]]
        for c, grupo in enumerate(grupos):
            marco_grupo = ttk.Frame(panel_izq, style="Gym.TFrame")
            marco_grupo.grid(row=1, column=c, sticky="nw", padx=(0, 12))
            for f, (clave, etiqueta) in enumerate(grupo):
                ttk.Label(
                    marco_grupo, text=f"{etiqueta}:", style="Gym.TLabel"
                ).grid(row=f, column=0, sticky="e", padx=(4, 4), pady=5)
                entry = ttk.Entry(marco_grupo, width=13, style="Gym.TEntry")
                entry.grid(row=f, column=1, sticky="w", padx=(0, 4), pady=5)
                self.entries_soma[clave] = entry

        barra = ttk.Frame(panel_izq, style="Gym.TFrame")
        barra.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))

        botones = [
            ("CARGAR ISAK", self.cargar_somatotipo_isak, False),
            ("CARGAR PESO/TALLA (ANTRO)", self.cargar_somatotipo_antro, False),
            ("CALCULAR", self.calcular_somatotipo, True),
            ("LIMPIAR", self.limpiar_somatotipo, False),
        ]
        for i, (texto, comando, primario) in enumerate(botones):
            tk.Button(
                barra,
                text=texto,
                command=comando,
                font=("Impact", 12),
                fg=NEGRO if primario else NEON,
                bg=NEON if primario else GRIS,
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=12,
                pady=6,
                cursor="hand2",
            ).grid(row=i // 2, column=i % 2, sticky="we", padx=(0, 6), pady=3)

        panel_der = ttk.Frame(marco, style="Gym.TFrame")
        panel_der.grid(row=2, column=1, sticky="nsew", padx=(4, 8), pady=4)
        marco.columnconfigure(1, weight=1)
        marco.rowconfigure(2, weight=1)

        ttk.Label(panel_der, text="RESULTADOS", style="Estado.TLabel").pack(
            anchor="w"
        )
        self.lbl_resultados_soma = tk.Label(
            panel_der,
            text="Captura las medidas y pulsa CALCULAR.",
            bg=GRIS_OSCURO,
            fg=BLANCO,
            justify="left",
            anchor="w",
            font=("Consolas", 11),
            padx=8,
            pady=6,
        )
        self.lbl_resultados_soma.pack(fill="x")

        self.canvas_soma = tk.Canvas(
            panel_der, bg=NEGRO, highlightthickness=0, width=500, height=440
        )
        self.canvas_soma.pack(pady=(4, 0))

        ttk.Label(
            panel_der,
            text="X = Ectomorfo - Endomorfo    |    "
            "Y = 2 x Mesomorfo - (Endomorfo + Ectomorfo)",
            style="Gym.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        self._dibujar_somatochart()

    @staticmethod
    def _valor_isak(valores):
        if not valores:
            return None
        if len(valores) == 1:
            return valores[0]
        if len(valores) == 2:
            return (valores[0] + valores[1]) / 2.0
        ordenados = sorted(valores)
        return ordenados[1]

    @staticmethod
    @staticmethod
    def _valor_isak(valores):
        if not valores:
            return None
        if len(valores) == 1:
            return valores[0]
        if len(valores) == 2:
            return (valores[0] + valores[1]) / 2.0
        ordenados = sorted(valores)
        return ordenados[1]

    def _nivel(valor):
        if valor < 2.75:
            return "bajo"
        if valor < 5.25:
            return "moderado"
        if valor < 7.25:
            return "alto"
        return "muy alto"

    @staticmethod
    def _clasificar_somatotipo(endo, meso, ecto):
        valores = [("Endomorfo", endo), ("Mesomorfo", meso), ("Ectomorfo", ecto)]
        orden = sorted(valores, key=lambda par: -par[1])
        if orden[0][1] - orden[2][1] <= 1.0:
            return "Central (equilibrado)"
        if orden[0][1] - orden[1][1] > 0.5:
            return f"{orden[0][0]} dominante"
        return f"Transición {orden[0][0].lower()}/{orden[1][0].lower()}"

    def cargar_somatotipo_isak(self, silencioso=False):
        if self.id_paciente_antro is None:
            if not silencioso:
                messagebox.showwarning(
                    "Seguimiento",
                    "Selecciona un paciente (campo Nombre) para el seguimiento.",
                )
            return False
        registros = database.obtener_perfil_isak(self.id_paciente_antro)
        if not registros:
            if silencioso:
                self.lbl_resultados_soma.configure(
                    text="Sin perfil ISAK guardado. Captura y guarda el "
                    "perfil en la pestaña Antropometría."
                )
                self._dibujar_somatochart()
            else:
                messagebox.showinfo(
                    "Somatotipo", "Este paciente no tiene perfil ISAK guardado."
                )
            return False
        datos = json.loads(registros[0]["datos"])
        etiquetas = dict(SOMATOTIPO_CAMPOS)
        faltantes = []
        avisos = []
        for clave, origen in SOMATOTIPO_ISAK.items():
            valores = []
            for i in (1, 2, 3):
                texto = (
                    str(datos.get(f"{origen}_{i}") or "")
                    .strip()
                    .replace(",", ".")
                )
                if texto:
                    try:
                        valores.append(float(texto))
                    except ValueError:
                        pass
            if not valores:
                faltantes.append(etiquetas[clave])
                continue
            final = self._valor_isak(valores)
            entry = self.entries_soma[clave]
            entry.delete(0, "end")
            entry.insert(0, f"{final:.6g}")
            if len(valores) == 2:
                tolerancia = (
                    ISAK_TOLERANCIA_PLIEGUES
                    if clave in ISAK_PLIEGUES
                    else ISAK_TOLERANCIA_OTROS
                )
                media = (valores[0] + valores[1]) / 2.0
                if media > 0 and abs(valores[0] - valores[1]) / media > tolerancia:
                    avisos.append(
                        f"{etiquetas[clave]}: {valores[0]:g} / {valores[1]:g} "
                        f"(dif. {100 * abs(valores[0] - valores[1]) / media:.1f}% "
                        f"> {tolerancia * 100:g}%)"
                    )
        if faltantes and not silencioso:
            messagebox.showinfo(
                "Somatotipo",
                "Sin dato en el perfil ISAK: " + ", ".join(faltantes),
            )
        if avisos and not silencioso:
            messagebox.showinfo(
                "ISAK - tolerancia",
                "Medidas 2da toma fuera de tolerancia "
                "(tomar 3ra medida):\n" + "\n".join(avisos),
            )
        return True

    def cargar_somatotipo_antro(self):
        if self.id_paciente_antro is None:
            messagebox.showwarning(
                "Seguimiento",
                "Selecciona un paciente (campo Nombre) para el seguimiento.",
            )
            return
        filas = database.obtener_antropometria()
        fila = next(
            (f for f in filas if f["paciente_id"] == self.id_paciente_antro),
            None,
        )
        if fila is None:
            messagebox.showinfo(
                "Somatotipo", "Este paciente no tiene antropometría guardada."
            )
            return
        rellenos = 0
        for clave, columna in (("peso", "peso"), ("estatura", "altura")):
            texto = str(fila[columna] or "").strip().replace(",", ".")
            if not texto:
                continue
            try:
                valor = float(texto)
            except ValueError:
                continue
            entry = self.entries_soma[clave]
            entry.delete(0, "end")
            entry.insert(0, f"{valor:g}")
            rellenos += 1
        if not rellenos:
            messagebox.showinfo(
                "Somatotipo",
                "El registro de antropometría no tiene peso ni estatura.",
            )

    def limpiar_somatotipo(self):
        for entry in self.entries_soma.values():
            entry.delete(0, "end")
        self.lbl_resultados_soma.configure(
            text="Captura las medidas y pulsa CALCULAR."
        )
        self._dibujar_somatochart()

    def calcular_somatotipo(self, silencioso=False):
        etiquetas = dict(SOMATOTIPO_CAMPOS)
        datos = {}
        faltantes = []
        invalidos = []
        for clave, entry in self.entries_soma.items():
            texto = entry.get().strip().replace(",", ".")
            if not texto:
                faltantes.append(etiquetas[clave])
                continue
            try:
                datos[clave] = float(texto)
            except ValueError:
                invalidos.append(etiquetas[clave])
        if faltantes or invalidos:
            if silencioso:
                avisos = []
                if faltantes:
                    avisos.append("faltan " + ", ".join(faltantes))
                if invalidos:
                    avisos.append("no numéricos " + ", ".join(invalidos))
                self.lbl_resultados_soma.configure(
                    text="Datos incompletos: " + "; ".join(avisos) + "."
                )
                self._dibujar_somatochart()
                return False
            if faltantes:
                messagebox.showwarning(
                    "Validación", "Falta el dato: " + ", ".join(faltantes) + "."
                )
            else:
                messagebox.showwarning(
                    "Validación",
                    "Valor no numérico en: " + ", ".join(invalidos) + ".",
                )
            return False
        if datos["peso"] <= 0 or datos["estatura"] <= 0:
            if silencioso:
                self.lbl_resultados_soma.configure(
                    text="Datos incompletos: peso y estatura deben ser "
                    "mayores que cero."
                )
                self._dibujar_somatochart()
                return False
            messagebox.showwarning(
                "Validación", "Peso y estatura deben ser mayores que cero."
            )
            return False

        sum3 = datos["triceps"] + datos["subescapular"] + datos["supraespinal"]
        xc = sum3 * (170.18 / datos["estatura"])
        endo = -0.7182 + 0.1451 * xc - 0.00068 * xc ** 2 + 0.0000014 * xc ** 3
        cag = datos["brazo_flexionado"] - datos["triceps"] / 10.0
        ccg = datos["pierna_maximo"] - datos["pierna_medial"] / 10.0
        meso = (
            0.858 * datos["humero"]
            + 0.601 * datos["femur"]
            + 0.188 * cag
            + 0.161 * ccg
            - 0.131 * datos["estatura"]
            + 4.5
        )
        hwr = datos["estatura"] / (datos["peso"] ** (1.0 / 3.0))
        if hwr >= 40.75:
            ecto = 0.732 * hwr - 28.58
            rama = "HWR >= 40.75"
        elif hwr > 38.25:
            ecto = 0.463 * hwr - 17.63
            rama = "38.25 < HWR < 40.75"
        else:
            ecto = 0.1
            rama = "HWR <= 38.25"

        e = max(round(endo, 1), 0.1)
        m = max(round(meso, 1), 0.1)
        c = max(round(ecto, 1), 0.1)
        x = round(c - e, 1)
        y = round(2 * m - (e + c), 1)

        texto = (
            f"Somatotipo: {e:.1f} - {m:.1f} - {c:.1f}\n"
            f"Endomorfo {e:.1f} ({self._nivel(e)})  |  "
            f"Mesomorfo {m:.1f} ({self._nivel(m)})  |  "
            f"Ectomorfo {c:.1f} ({self._nivel(c)})\n"
            f"Coordenadas:  X = {x:.1f}   Y = {y:.1f}\n"
            f"HWR = {hwr:.2f} ({rama})\n"
            f"Suma 3 pliegues = {sum3:.1f} mm  ->  corregida = {xc:.1f}\n"
            f"Brazo corregido = {cag:.1f} cm  |  "
            f"Pierna corregida = {ccg:.1f} cm\n"
            f"Clasificación: {self._clasificar_somatotipo(e, m, c)}"
        )
        self.lbl_resultados_soma.configure(text=texto)
        self._dibujar_somatochart((e, m, c, x, y))
        return True

    def _dibujar_somatochart(self, punto=None):
        canvas = self.canvas_soma
        canvas.delete("all")
        ancho = int(canvas.cget("width"))
        alto = int(canvas.cget("height"))

        x_min, x_max = -8.0, 8.0
        y_min, y_max = -8.0, 14.0
        escala_y = min(
            ancho / ((x_max - x_min) * math.sqrt(3)),
            alto / (y_max - y_min),
        )
        escala_x = escala_y * math.sqrt(3)
        margen_x = (ancho - (x_max - x_min) * escala_x) / 2
        margen_y = (alto - (y_max - y_min) * escala_y) / 2

        def px(valor):
            return margen_x + (valor - x_min) * escala_x

        def py(valor):
            return margen_y + (y_max - valor) * escala_y

        rejilla = "#262626"
        for v in range(-8, 15, 2):
            canvas.create_line(px(v), py(y_min), px(v), py(y_max), fill=rejilla)
            canvas.create_line(px(x_min), py(v), px(x_max), py(v), fill=rejilla)

        canvas.create_line(
            px(x_min), py(0), px(x_max), py(0), fill=GRIS_TEXTO, width=1
        )
        canvas.create_line(
            px(0), py(y_min), px(0), py(y_max), fill=GRIS_TEXTO, width=1
        )
        for v in range(-6, 7, 2):
            canvas.create_text(
                px(v),
                py(0) + 10,
                text=str(v),
                fill=GRIS_TEXTO,
                font=("Segoe UI", 8),
            )
        for v in range(-6, 13, 2):
            canvas.create_text(
                px(0) - 8,
                py(v),
                text=str(v),
                fill=GRIS_TEXTO,
                font=("Segoe UI", 8),
                anchor="e",
            )

        v_endo = (px(-6), py(-6))
        v_ecto = (px(6), py(-6))
        v_meso = (px(0), py(12))
        lado = math.hypot(v_ecto[0] - v_endo[0], v_ecto[1] - v_endo[1])

        def angulo(cx, cy, xy):
            return math.degrees(math.atan2(cy - xy[1], xy[0] - cx)) % 360

        def arco(centro, a, b):
            cx, cy = centro
            ra = angulo(cx, cy, a)
            rb = angulo(cx, cy, b)
            bx = (a[0] - cx) + (b[0] - cx)
            by = (a[1] - cy) + (b[1] - cy)
            norm = math.hypot(bx, by) or 1.0
            medio = (cx + bx / norm * lado, cy + by / norm * lado)
            rm = angulo(cx, cy, medio)
            recorrido = (rb - ra) % 360
            if (rm - ra) % 360 <= recorrido:
                extent = recorrido
            else:
                extent = -((ra - rb) % 360)
            canvas.create_arc(
                cx - lado,
                cy - lado,
                cx + lado,
                cy + lado,
                start=ra,
                extent=extent,
                style=tk.ARC,
                outline=NEON,
                width=2,
            )

        arco(v_meso, v_endo, v_ecto)
        arco(v_endo, v_meso, v_ecto)
        arco(v_ecto, v_endo, v_meso)

        canvas.create_text(
            px(-6),
            py(-6) + 18,
            text="ENDOMORPHY",
            fill=GRIS_TEXTO,
            font=("Segoe UI", 9, "bold"),
        )
        canvas.create_text(
            px(6),
            py(-6) + 18,
            text="ECTOMORPHY",
            fill=GRIS_TEXTO,
            font=("Segoe UI", 9, "bold"),
        )
        canvas.create_text(
            px(0),
            py(12) - 16,
            text="MESOMORPHY",
            fill=GRIS_TEXTO,
            font=("Segoe UI", 9, "bold"),
        )
        canvas.create_text(
            px(0),
            py(0) - 10,
            text="CENTRO 4-4-4",
            fill="#5A5A5A",
            font=("Segoe UI", 8),
        )

        if punto is not None:
            e, m, c, x, y = punto
            cxp, cyp = px(x), py(y)
            radio = 7
            canvas.create_oval(
                cxp - radio,
                cyp - radio,
                cxp + radio,
                cyp + radio,
                fill=NARANJA,
                outline=BLANCO,
                width=2,
            )
            if cxp + radio + 90 <= ancho:
                tx, anchor = cxp + radio + 5, "w"
            elif cxp - radio - 90 >= 0:
                tx, anchor = cxp - radio - 5, "e"
            else:
                tx, anchor = cxp, "center"
            dy = -8 if anchor != "center" else -radio - 26
            canvas.create_text(
                tx,
                cyp + dy,
                text=f"{e:.1f}-{m:.1f}-{c:.1f}",
                fill=NEON,
                font=("Segoe UI", 11, "bold"),
                anchor=anchor,
            )
            canvas.create_text(
                tx,
                cyp + dy + 16,
                text=f"X {x:.1f}  Y {y:.1f}",
                fill=BLANCO,
                font=("Segoe UI", 9),
                anchor=anchor,
            )


if __name__ == "__main__":
    App().mainloop()
