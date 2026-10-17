import tkinter as tk
from tkinter import messagebox, ttk

import database

ETIQUETAS = [
    ("deporte", "Deporte"),
    ("fecha", "Fecha"),
    ("nombre", "Nombre"),
    ("dob", "DOB"),
    ("fecha_nacimiento", "Fecha de nacimiento"),
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


class DialogoPacientes(tk.Toplevel):
    def __init__(self, parent, pacientes):
        super().__init__(parent)
        self.title("Seleccionar paciente")
        self.configure(bg=NEGRO)
        self.geometry("620x400")
        self.transient(parent)
        self.grab_set()

        self.seleccion = None

        ttk.Label(
            self,
            text="Selecciona el paciente a editar",
            style="Estado.TLabel",
        ).pack(anchor="w", padx=12, pady=(12, 6))

        contenedor = ttk.Frame(self, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=12, pady=6)

        columnas = ("codigo", "nombre", "deporte", "gimnasio", "fecha")
        self.tabla = ttk.Treeview(
            contenedor, columns=columnas, show="headings", style="Gym.Treeview"
        )
        encabezados = {
            "codigo": "Código",
            "nombre": "Nombre",
            "deporte": "Deporte",
            "gimnasio": "Gimnasio",
            "fecha": "Fecha",
        }
        for col in columnas:
            self.tabla.heading(col, text=encabezados[col])
            self.tabla.column(col, width=110, anchor="w")

        scroll = ttk.Scrollbar(
            contenedor, orient="vertical", command=self.tabla.yview
        )
        self.tabla.configure(yscrollcommand=scroll.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for paciente in pacientes:
            self.tabla.insert(
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

        self.tabla.bind("<Double-1>", lambda _e: self.confirmar())

        barra = ttk.Frame(self, style="Gym.TFrame")
        barra.pack(fill="x", padx=12, pady=12)
        tk.Button(
            barra,
            text="EDITAR",
            command=self.confirmar,
            font=("Impact", 12),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
        ).pack(side="left")
        tk.Button(
            barra,
            text="CANCELAR",
            command=self.destroy,
            font=("Impact", 12),
            fg=NEON,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=8)

    def confirmar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showwarning(
                "Selección", "Selecciona un paciente de la lista."
            )
            return
        self.seleccion = int(seleccion[0])
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nutrición Deportiva")
        self.geometry("900x780")
        self.configure(bg=NEGRO)

        self.configurar_tema()

        database.init_db()

        self.id_paciente = None
        self.id_paciente_antro = None

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.entries = {}
        self.entries_antro = {}

        marco_paciente = self.crear_formulario(
            self.notebook,
            "  💪 Paciente  ",
            ETIQUETAS,
            [
                ("NUEVO PACIENTE", self.nuevo_paciente),
                ("EDITAR PACIENTE", self.editar_paciente),
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

        self._configurar_autocompletado()

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
        self.lbl_estado.configure(text="Nuevo paciente (sin guardar)")
        self.entries["nombre"].focus_set()

    def editar_paciente(self):
        pacientes = database.obtener_pacientes()
        if not pacientes:
            messagebox.showinfo("Editar", "No hay pacientes registrados.")
            return
        dialogo = DialogoPacientes(self, pacientes)
        self.wait_window(dialogo)
        if dialogo.seleccion is None:
            return
        paciente = database.obtener_paciente(dialogo.seleccion)
        if not paciente:
            return
        for clave, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, paciente.get(clave, "") or "")
        self.id_paciente = paciente["id"]
        self.lbl_estado.configure(
            text=f"Editando {paciente.get('codigo') or ''} — "
            f"{paciente.get('nombre', '')}"
        )

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

    def _iniciar_seguimiento(self, paciente):
        self.id_paciente_antro = paciente["id"]
        self.lbl_antro.configure(
            text=f"Seguimiento de {paciente.get('codigo') or ''} — "
            f"{paciente.get('nombre', '')}"
        )
        entry_id = self.entries_isak.get("id_paciente")
        if entry_id is not None:
            entry_id.state(["!readonly"])
            entry_id.delete(0, "end")
            entry_id.insert(0, paciente.get("codigo") or "")
            entry_id.state(["readonly"])
        self.notebook.select(self.marco_antro)
        self.entries_antro["fecha"].focus_set()

    def guardar(self):
        datos = self._leer(self.entries)
        if not datos["nombre"]:
            messagebox.showwarning("Validación", "El nombre es obligatorio.")
            return
        try:
            if self.id_paciente is None:
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


if __name__ == "__main__":
    App().mainloop()
