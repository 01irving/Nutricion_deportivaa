"""
Pestaña Fórmulas predictivas - Cálculo de energía.
GEB seleccionable: Schofield (NUTR107x Formula Card) con GEE = GEB x PAL
x h/24 + EEE del Compendio de Actividades Físicas 2011 (mets.csv), o
Valencia con GET = GEB x factor de actividad.
"""
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

import database

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"


def calcular_edad(fecha_nacimiento, referencia=None):
    """Edad en años (int) a partir de la fecha de nacimiento (texto)."""
    if not fecha_nacimiento:
        return None
    referencia = referencia or date.today()
    texto = str(fecha_nacimiento).strip()
    formatos = (
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
        "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d %H:%M:%S",
    )
    nacimiento = None
    for fmt in formatos:
        try:
            nacimiento = datetime.strptime(texto, fmt).date()
            break
        except ValueError:
            continue
    if nacimiento is None:
        # Intentar tomar solo la fecha si viene con hora/espacio
        solo_fecha = texto.split(" ")[0]
        for fmt in formatos:
            try:
                nacimiento = datetime.strptime(solo_fecha, fmt).date()
                break
            except ValueError:
                continue
    if nacimiento is None:
        return None
    edad = referencia.year - nacimiento.year - (
        (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day)
    )
    return edad if edad >= 0 else None


def bmr_schofield(peso, edad, sexo):
    """BMR Schofield (kcal/día). Devuelve (valor, etiqueta_rango)."""
    if edad < 3:
        valor = (59.512 if sexo == "H" else 58.317) * peso - (
            30.4 if sexo == "H" else 31.1
        )
        return valor, "<3 años"
    if edad < 10:
        valor = (22.706 if sexo == "H" else 20.315) * peso + (
            504.3 if sexo == "H" else 485.9
        )
        return valor, "3-10 años"
    if edad < 18:
        valor = (17.686 if sexo == "H" else 13.384) * peso + (
            658.2 if sexo == "H" else 692.6
        )
        return valor, "10-18 años"
    if edad < 30:
        valor = (15.057 if sexo == "H" else 14.818) * peso + (
            692.2 if sexo == "H" else 486.6
        )
        return valor, "18-30 años"
    if edad < 60:
        valor = (11.472 if sexo == "H" else 8.126) * peso + (
            873.1 if sexo == "H" else 845.6
        )
        return valor, "30-60 años"
    valor = (11.711 if sexo == "H" else 9.082) * peso + (
        587.7 if sexo == "H" else 658.5
    )
    return valor, ">60 años"


def bmr_valencia(peso, edad, sexo):
    """GEB con las ecuaciones de Valencia (kcal/día), solo desde los 18 años.
    Devuelve (valor, etiqueta_rango). Si el sujeto es menor de 18 años se
    usa Schofield para no romper el cálculo.
    """
    if edad < 18:
        valor, rango = bmr_schofield(peso, edad, sexo)
        return valor, f"{rango} (Schofield; Valencia desde 18 años)"
    if edad < 30:
        valor = (13.37 if sexo == "H" else 11.02) * peso + (
            747 if sexo == "H" else 679
        )
        return valor, "18-30 años"
    if edad < 60:
        valor = (13.08 if sexo == "H" else 10.92) * peso + (
            693 if sexo == "H" else 677
        )
        return valor, "30-60 años"
    valor = (14.21 if sexo == "H" else 10.98) * peso + (
        429 if sexo == "H" else 520
    )
    return valor, ">60 años"


# Fórmulas de GEB disponibles en la pestaña (etiqueta -> función)
FORMULAS_GEB = {
    "Schofield-METs": bmr_schofield,
    "Valencia": bmr_valencia,
}

# Factor de actividad para Valencia (GET = GEB x factor)
FACTORES_ACTIVIDAD = {
    "Sedentario (1.2)": 1.2,
    "Actividad ligera (1.375)": 1.375,
    "Actividad moderada (1.55)": 1.55,
    "Actividad intensa (1.725)": 1.725,
    "Actividad muy intensa (1.9)": 1.9,
}


class FormulasTab:
    def __init__(self, app):
        self.app = app
        self.tee = None
        self.peso = None
        self.resultado = None

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  ⚡ Fórmulas predictivas  ")
        self._pestana = self.marco  # widget gestionado por el notebook

        # --- Área con scroll vertical ---
        self.canvas = tk.Canvas(
            self.marco, bg=GRIS_OSCURO, highlightthickness=0, bd=0
        )
        self.scrollbar = ttk.Scrollbar(
            self.marco, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True)

        contenido = ttk.Frame(self.canvas, style="Gym.TFrame")
        self._canvas_window = self.canvas.create_window(
            (0, 0), window=contenido, anchor="nw"
        )

        def _on_config(_e):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        def _on_canvas_width(event):
            self.canvas.itemconfigure(self._canvas_window, width=event.width)

        contenido.bind("<Configure>", _on_config)
        self.canvas.bind("<Configure>", _on_canvas_width)
        for widget in (self.canvas, contenido):
            widget.bind(
                "<MouseWheel>",
                lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"),
            )
        self.marco = contenido

        titulo = tk.Label(
            self.marco,
            text="FÓRMULAS PREDICTIVAS DE ENERGÍA",
            font=("Impact", 20),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 6))

        contenedor = ttk.Frame(self.marco, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=8, pady=4)

        # ----- Datos del sujeto -----
        datos = ttk.LabelFrame(contenedor, text="Datos del sujeto", padding=8)
        datos.grid(row=0, column=0, sticky="new", padx=(0, 8))

        self.peso_var = tk.StringVar(value="70")
        self.edad_var = tk.StringVar(value="25")
        self.sexo_var = tk.StringVar(value="H")
        self._campo(datos, 0, "Peso (kg):", self.peso_var)
        self._campo(datos, 1, "Edad (años):", self.edad_var)
        ttk.Label(datos, text="Sexo:", style="Gym.TLabel").grid(
            row=2, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Combobox(
            datos, textvariable=self.sexo_var, values=["H", "M"],
            state="readonly", width=6, style="Gym.TCombobox",
        ).grid(row=2, column=1, sticky="w", padx=4, pady=5)

        self.talla_var = tk.StringVar(value="")
        ttk.Label(datos, text="Talla (cm):", style="Gym.TLabel").grid(
            row=3, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Entry(datos, textvariable=self.talla_var, width=10,
                  style="Gym.TEntry").grid(row=3, column=1, sticky="w", padx=4, pady=5)

        # Fórmula de GEB: Schofield-METs (la de siempre) o Valencia
        self.formula_var = tk.StringVar(value="Schofield-METs")
        ttk.Label(datos, text="Fórmula GEB:", style="Gym.TLabel").grid(
            row=4, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Combobox(
            datos, textvariable=self.formula_var,
            values=list(FORMULAS_GEB), state="readonly", width=16,
            style="Gym.TCombobox",
        ).grid(row=4, column=1, sticky="w", padx=4, pady=5)

        # Nivel de actividad para Valencia (GET = GEB x factor)
        self.actividad_var = tk.StringVar(
            value="Actividad moderada (1.55)"
        )
        ttk.Label(datos, text="Actividad:", style="Gym.TLabel").grid(
            row=5, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Combobox(
            datos, textvariable=self.actividad_var,
            values=list(FACTORES_ACTIVIDAD), state="readonly", width=24,
            style="Gym.TCombobox",
        ).grid(row=5, column=1, sticky="w", padx=4, pady=5)

        # Los datos del paciente se cargan de forma directa cuando se
        # selecciona un paciente (ver cargar()). Sin botones aquí.

        # ----- Actividad / MET -----
        act = ttk.LabelFrame(
            contenedor, text="Actividad física (Compendio METs)", padding=8
        )
        act.grid(row=1, column=0, sticky="new", padx=(0, 8), pady=(8, 0))
        self.frame_mets = act  # se contrae al elegir Valencia

        ttk.Label(act, text="Categoría:", style="Gym.TLabel").grid(
            row=0, column=0, sticky="e", padx=4, pady=5
        )
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(
            act, textvariable=self.cat_var, state="readonly", width=30,
            style="Gym.TCombobox",
        )
        self.cat_combo.grid(row=0, column=1, columnspan=3, sticky="w", padx=4, pady=5)
        self.cat_combo.bind("<<ComboboxSelected>>", self._on_categoria)

        ttk.Label(act, text="Actividad:", style="Gym.TLabel").grid(
            row=1, column=0, sticky="e", padx=4, pady=5
        )
        self.act_var = tk.StringVar()
        self.act_combo = ttk.Combobox(
            act, textvariable=self.act_var, state="readonly", width=52,
            style="Gym.TCombobox",
        )
        self.act_combo.grid(row=1, column=1, columnspan=3, sticky="w", padx=4, pady=5)
        self.act_combo.bind("<<ComboboxSelected>>", self._on_actividad)

        ttk.Label(act, text="METs:", style="Gym.TLabel").grid(
            row=2, column=0, sticky="e", padx=4, pady=5
        )
        self.mets_var = tk.StringVar(value="")
        self.mets_entry = ttk.Entry(act, textvariable=self.mets_var, width=8,
                                    style="Gym.TEntry")
        self.mets_entry.grid(row=2, column=1, sticky="w", padx=4, pady=5)

        ttk.Label(act, text="Horas de ejercicio (h):", style="Gym.TLabel").grid(
            row=2, column=2, sticky="e", padx=4, pady=5
        )
        self.horas_var = tk.StringVar(value="1")
        self.horas_entry = ttk.Entry(act, textvariable=self.horas_var, width=8,
                                     style="Gym.TEntry")
        self.horas_entry.grid(row=2, column=3, sticky="w", padx=4, pady=5)
        for evento in ("<KeyRelease>", "<FocusOut>"):
            self.horas_entry.bind(
                evento, lambda _e: self._sincronizar_horas("ejercicio")
            )

        # ----- PAL / actividad diaria -----
        pal = ttk.LabelFrame(
            contenedor, text="Actividad diaria (GEE = BMR x PAL x h/24)", padding=8
        )
        pal.grid(row=2, column=0, sticky="new", padx=(0, 8), pady=(8, 0))
        self.frame_pal = pal  # se contrae al elegir Valencia

        ttk.Label(pal, text="Nivel PAL:", style="Gym.TLabel").grid(
            row=0, column=0, sticky="e", padx=4, pady=5
        )
        self.pal_var = tk.StringVar(value="1.6")
        self.pal_combo = ttk.Combobox(
            pal,
            textvariable=self.pal_var,
            values=[
                "Sedentario (<1.6)",
                "Moderadamente activo (1.6-2.0)",
                "Intensamente activo (>2.0)",
                "Reposo (1.2)",
            ],
            state="readonly",
            width=28,
            style="Gym.TCombobox",
        )
        self.pal_combo.grid(row=0, column=1, sticky="w", padx=4, pady=5)
        self.pal_combo.bind("<<ComboboxSelected>>", self._on_pal)

        ttk.Label(pal, text="PAL manual:", style="Gym.TLabel").grid(
            row=1, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Entry(pal, textvariable=self.pal_var, width=10,
                  style="Gym.TEntry").grid(
            row=1, column=1, sticky="w", padx=4, pady=5
        )

        ttk.Label(pal, text="Horas NO ejercicio (h/24):", style="Gym.TLabel").grid(
            row=2, column=0, sticky="e", padx=4, pady=5
        )
        self.h24_var = tk.StringVar(value="23")
        self.h24_entry = ttk.Entry(pal, textvariable=self.h24_var, width=10,
                                   style="Gym.TEntry")
        self.h24_entry.grid(row=2, column=1, sticky="w", padx=4, pady=5)
        for evento in ("<KeyRelease>", "<FocusOut>"):
            self.h24_entry.bind(
                evento, lambda _e: self._sincronizar_horas("no_ejercicio")
            )

        # ----- Botones -----
        barra = ttk.Frame(contenedor, style="Gym.TFrame")
        barra.grid(row=3, column=0, sticky="w", pady=(10, 0))
        botones = [
            ("CALCULAR", self.calcular, True),
            ("GUARDAR", self.guardar, False),
            ("LIMPIAR", self.limpiar, False),
        ]
        for texto, comando, primario in botones:
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

        # ----- Resultados -----
        res = ttk.LabelFrame(contenedor, text="Resultados", padding=8)
        res.grid(row=0, column=1, rowspan=4, sticky="nsew", padx=(8, 0))
        contenedor.columnconfigure(1, weight=1)
        self.res_labels = {}
        self.lbl_rows = {}  # etiquetas de la columna izquierda de Resultados
        filas = [
            ("bmr", "GEB (Schofield-METs)"),
            ("rango", "Rango de edad"),
            ("gee", "GEE (GEB x PAL x h/24)"),
            ("eee", "EEE (MET x peso x h)"),
            ("tee", "GET/TEE (GEE + EEE)"),
            ("ea", "EA (EI - EEE)"),
        ]
        for i, (clave, etiqueta) in enumerate(filas):
            lbl_row = ttk.Label(res, text=f"{etiqueta}:", style="Gym.TLabel")
            lbl_row.grid(row=i, column=0, sticky="w", padx=4, pady=4)
            self.lbl_rows[clave] = lbl_row
            if clave == "bmr":
                self.lbl_row_bmr = lbl_row  # se renombra según la fórmula
            lbl = tk.Label(res, text="—", fg=NEON, bg=GRIS_OSCURO,
                           font=("Segoe UI", 11, "bold"))
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=4)
            self.res_labels[clave] = lbl

        # Contraer los cuadros que no aplican según la fórmula elegida
        self.formula_var.trace_add("write", self._on_formula)
        self._on_formula()

        self._cargar_categorias()

    def _campo(self, parent, fila, etiqueta, var):
        ttk.Label(parent, text=etiqueta, style="Gym.TLabel").grid(
            row=fila, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Entry(parent, textvariable=var, width=10, style="Gym.TEntry").grid(
            row=fila, column=1, sticky="w", padx=4, pady=5
        )

    def _cargar_categorias(self):
        categorias = database.get_mets_categorias()
        self.cat_combo["values"] = categorias
        if categorias:
            self.cat_combo.current(0)
            self._on_categoria()

    def cargar(self, paciente_id):
        """Carga directa y silenciosa de los datos del paciente activo."""
        self.cargar_datos_paciente(paciente_id=paciente_id, silencioso=True)

    def refrescar(self):
        """Recarga los datos al entrar a la pestaña: primero el formulario
        de Paciente del paciente activo; si falta algo, el registro."""
        self.cargar_datos_paciente(
            paciente_id=getattr(self.app, "id_paciente_antro", None),
            silencioso=True)

    def cargar_datos_paciente(self, paciente_id=None, silencioso=False):
        """Toma peso y talla de la ficha del paciente; si falta alguno,
        usa la antropometría más reciente. La edad sale de la fecha de
        nacimiento.
        """
        paciente_id = paciente_id or getattr(
            self.app, "id_paciente_antro", None)
        if paciente_id is None:
            if not silencioso:
                messagebox.showwarning(
                    "Fórmulas predictivas",
                    "Selecciona un paciente antes de tomar datos.",
                )
            return

        avisos = []
        paciente = database.obtener_paciente(paciente_id) or {}
        # Preferir el formulario de la pestaña Paciente cuando refleja al
        # paciente activo (valores en pantalla, aunque no estén guardados).
        entradas = getattr(self.app, "entries", None) or {}
        id_form = getattr(self.app, "id_paciente", None)
        if id_form is not None and id_form == paciente_id:
            for campo in ("peso", "talla", "genero", "fecha_nacimiento",
                          "dob"):
                entry = entradas.get(campo)
                if entry is None:
                    continue
                try:
                    texto = str(entry.get()).strip()
                except Exception:
                    texto = ""
                if texto:
                    paciente[campo] = texto

        peso_texto = str(paciente.get("peso") or "").strip().replace(",", ".")
        talla_texto = str(paciente.get("talla") or "").strip().replace(",", ".")
        origen_peso = "ficha del paciente" if peso_texto else ""
        origen_talla = "ficha del paciente" if talla_texto else ""

        # --- Respaldo: antropometría más reciente del paciente ---
        if not peso_texto or not talla_texto:
            filas = database.obtener_antropometria()
            fila = next(
                (f for f in filas if f["paciente_id"] == paciente_id), None
            )
            if fila is not None:
                if not peso_texto:
                    peso_texto = (
                        str(fila["peso"] or "").strip().replace(",", ".")
                    )
                    origen_peso = "antropometría" if peso_texto else ""
                if not talla_texto:
                    talla_texto = (
                        str(fila["altura"] or "").strip().replace(",", ".")
                    )
                    origen_talla = "antropometría" if talla_texto else ""
            if not peso_texto:
                avisos.append("El paciente no tiene peso (ficha ni antropometría).")
            if not talla_texto:
                avisos.append("El paciente no tiene talla (ficha ni antropometría).")

        try:
            self.peso_var.set(f"{float(peso_texto):g}")
        except ValueError:
            self.peso_var.set("")
            if peso_texto:
                avisos.append("El peso guardado no es válido.")
        else:
            if origen_peso == "antropometría":
                avisos.append("Peso tomado de antropometría (sin peso en la ficha).")

        try:
            self.talla_var.set(f"{float(talla_texto):g}")
        except ValueError:
            self.talla_var.set("")
            if talla_texto:
                avisos.append("La talla guardada no es válida.")
        else:
            if origen_talla == "antropometría":
                avisos.append("Talla tomada de antropometría (sin talla en la ficha).")

        # --- Sexo desde el género de la ficha del paciente ---
        genero = str(paciente.get("genero") or "").strip().lower()
        mapa_sexo = {
            "h": "H", "hombre": "H", "masculino": "H", "varón": "H",
            "varon": "H", "masc": "H",
            "m": "M", "mujer": "M", "femenino": "M", "f": "M", "fem": "M",
        }
        if genero in mapa_sexo:
            self.sexo_var.set(mapa_sexo[genero])
        elif genero:
            avisos.append(
                f"Género «{paciente.get('genero')}» no reconocido; "
                "usa Hombre o Mujer en la ficha."
            )

        # --- Edad desde la fecha de nacimiento del paciente ---
        fecha_nac = paciente.get("fecha_nacimiento") or paciente.get("dob")
        edad = calcular_edad(fecha_nac)
        if edad is not None:
            self.edad_var.set(str(edad))
        else:
            self.edad_var.set("")
            avisos.append("No se pudo calcular la edad (fecha de nacimiento).")

        if avisos and not silencioso:
            messagebox.showinfo("Fórmulas predictivas", "\n".join(avisos))
        elif not avisos and not silencioso:
            messagebox.showinfo(
                "Fórmulas predictivas",
                "Peso, talla y sexo tomados de la ficha del paciente, "
                "edad calculada por fecha de nacimiento.",
            )

    def _on_categoria(self, event=None):
        categoria = self.cat_var.get()
        actividades = database.get_mets_por_categoria(categoria)
        etiquetas = [
            f"{a['codigo']}  {a['mets']:.1f}  {a['actividad']}"
            for a in actividades
        ]
        self.act_combo["values"] = etiquetas
        self._actividades = {e: a for e, a in zip(etiquetas, actividades)}
        if etiquetas:
            self.act_combo.current(0)
            self._on_actividad()

    def _on_actividad(self, event=None):
        elegido = self._actividades.get(self.act_var.get())
        if elegido:
            self.mets_var.set(f"{elegido['mets']:.1f}")

    def _on_pal(self, event=None):
        texto = self.pal_var.get()
        valores = {
            "Sedentario (<1.6)": "1.5",
            "Moderadamente activo (1.6-2.0)": "1.7",
            "Intensamente activo (>2.0)": "2.1",
            "Reposo (1.2)": "1.2",
        }
        if texto in valores:
            self.pal_var.set(valores[texto])

    def _on_formula(self, *_):
        """Al elegir Valencia contrae los cuadros que solo usa
        Schofield-METs (Compendio METs y PAL) y oculta los resultados que
        no aplican, dejando solo GEB, rango y GET; al volver a
        Schofield-METs todo se restaura. Limpia resultados previos para no
        mezclar cálculos de fórmulas distintas.
        """
        valencia = self.formula_var.get() == "Valencia"
        for marco in (self.frame_mets, self.frame_pal):
            (marco.grid_remove if valencia else marco.grid)()
        for clave in ("gee", "eee", "ea"):
            for widget in (self.lbl_rows[clave], self.res_labels[clave]):
                (widget.grid_remove if valencia else widget.grid)()
        self.lbl_row_bmr.configure(
            text=f"GEB ({self.formula_var.get() or 'Schofield-METs'}):"
        )
        self.limpiar()

    def _float(self, var, nombre):
        try:
            return float(str(var.get()).replace(",", "."))
        except ValueError:
            raise ValueError(f"{nombre} debe ser un número.")

    def _sincronizar_horas(self, origen):
        """Mantiene horas de ejercicio + horas de no ejercicio = 24."""
        if origen == "ejercicio":
            try:
                horas = float(self.horas_var.get().replace(",", "."))
            except ValueError:
                return
            horas = min(max(horas, 0.0), 24.0)
            self.h24_var.set(f"{24.0 - horas:g}")
        else:
            try:
                horas = float(self.h24_var.get().replace(",", "."))
            except ValueError:
                return
            horas = min(max(horas, 0.0), 24.0)
            self.horas_var.set(f"{24.0 - horas:g}")

    def calcular(self):
        try:
            peso = self._float(self.peso_var, "Peso")
            edad = self._float(self.edad_var, "Edad")
        except ValueError as error:
            messagebox.showwarning("Validación", str(error))
            return

        # GEB según la fórmula elegida; si la seleccionada no está
        # disponible se usa Schofield para no romper el flujo hacia
        # Equivalentes.
        nombre_formula = self.formula_var.get() or "Schofield-METs"
        funcion_bmr = FORMULAS_GEB.get(nombre_formula, bmr_schofield)

        factor = None
        if nombre_formula == "Valencia":
            # GET = GEB x factor de actividad (tabla de Valencia)
            factor = FACTORES_ACTIVIDAD.get(self.actividad_var.get(), 1.55)
            bmr, rango = funcion_bmr(peso, edad, self.sexo_var.get())
            gee = eee = ea = None
            met = horas = h24 = None
            pal = factor
            tee = bmr * factor
        else:
            try:
                met = self._float(self.mets_var, "METs")
                horas = self._float(self.horas_var, "Horas de ejercicio")
                pal = self._float(self.pal_var, "PAL")
                h24 = self._float(self.h24_var, "Horas NO ejercicio")
            except ValueError as error:
                messagebox.showwarning("Validación", str(error))
                return

            if not (0 <= horas <= 24):
                messagebox.showwarning(
                    "Validación",
                    "Las horas de ejercicio deben estar entre 0 y 24.",
                )
                return
            if not (0 <= h24 <= 24):
                messagebox.showwarning(
                    "Validación",
                    "Las horas sin ejercicio deben estar entre 0 y 24.",
                )
                return
            if horas + h24 > 24 + 1e-9:
                messagebox.showwarning(
                    "Validación",
                    "El día solo tiene 24 horas: ejercicio + no ejercicio "
                    "no puede superar 24 h.",
                )
                return

            bmr, rango = funcion_bmr(peso, edad, self.sexo_var.get())
            gee = bmr * pal * (h24 / 24.0)
            eee = met * peso * horas
            tee = gee + eee
            ea = tee - eee

        self.tee = tee
        self.peso = peso
        self.resultado = {
            "peso": peso,
            "edad": edad,
            "sexo": self.sexo_var.get(),
            "formula": nombre_formula,
            "factor_actividad": factor,
            "pal": pal,
            "horas_no_ejercicio": h24,
            "categoria": (
                "Valencia" if nombre_formula == "Valencia"
                else self.cat_var.get()
            ),
            "actividad": (
                self.actividad_var.get() if nombre_formula == "Valencia"
                else self.act_var.get()
            ),
            "mets": met,
            "horas_ejercicio": horas,
            "bmr": bmr,
            "rango_edad": rango,
            "gee": gee,
            "eee": eee,
            "tee": tee,
            "ea": ea,
        }

        self.lbl_row_bmr.configure(text=f"GEB ({nombre_formula}):")
        self.res_labels["bmr"].configure(text=f"{bmr:.0f} kcal/día")
        self.res_labels["rango"].configure(text=rango)
        self.res_labels["gee"].configure(
            text="—" if gee is None else f"{gee:.0f} kcal"
        )
        self.res_labels["eee"].configure(
            text="—" if eee is None else f"{eee:.0f} kcal"
        )
        self.res_labels["tee"].configure(text=f"{tee:.0f} kcal/día")
        self.res_labels["ea"].configure(
            text="—" if ea is None else f"{ea:.0f} kcal"
        )

    def limpiar(self):
        self.tee = None
        self.peso = None
        self.resultado = None
        for lbl in self.res_labels.values():
            lbl.configure(text="—")

    def guardar(self):
        if getattr(self, "resultado", None) is None:
            messagebox.showwarning(
                "Fórmulas predictivas",
                "Primero calcula los resultados antes de guardar.",
            )
            return
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            messagebox.showwarning(
                "Fórmulas predictivas",
                "Selecciona un paciente antes de guardar.",
            )
            return
        datos = dict(self.resultado, paciente_id=paciente_id)
        database.insert_formulas(datos)
        messagebox.showinfo(
            "Fórmulas predictivas",
            "Cálculo guardado para el paciente activo.",
        )
