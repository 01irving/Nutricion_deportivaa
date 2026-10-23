"""
Pestaña 5 Componentes - Fraccionamiento antropométrico del peso.

Implementa el método de Ross & Kerr (1993) / Kerr (1988) que divide la masa
corporal en piel, tejido adiposo, músculo, hueso y tejido residual.

Las medidas se toman de la pestaña Antropometría: peso y altura del registro
antropométrico y el resto del perfil ISAK del paciente activo.
"""
import json
import math
import tkinter as tk
from tkinter import messagebox, ttk

import antropometria_print
import database
from formulas_tab import calcular_edad

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

ALTURA_PHANTOM = 170.18
ALTURA_SENTADO_PHANTOM = 89.92

GRUPOS_IZQUIERDA = [
    (
        "Datos generales",
        [
            ("peso", "Peso / masa corporal (kg)", "entry"),
            ("estatura", "Talla / estatura (cm)", "entry"),
            ("talla_sentado", "Talla sentado (cm)", "entry"),
            ("sexo", "Sexo", "combo"),
            ("edad", "Edad (años)", "entry"),
        ],
        None,
    ),
    (
        "Masa adiposa: 6 pliegues (mm)",
        [
            ("triceps", "Tríceps (TPSF)", "entry"),
            ("subescapular", "Subescapular (SSSF)", "entry"),
            ("supraespinal", "Supraespinal (SISF)", "entry"),
            ("abdominal", "Abdominal (ABSF)", "entry"),
            ("muslo_anterior", "Muslo anterior / frontal (THSF)", "entry"),
            ("pierna_medial", "Pierna medial / pantorrilla (MCSF)", "entry"),
        ],
        None,
    ),
    (
        "Masa residual: diámetros y cintura (cm)",
        [
            ("torax_ap", "Tórax anteroposterior (D APCH)", "entry"),
            ("torax_transverso", "Tórax transverso (D TRCH)", "entry"),
            ("cintura", "Cintura mínima (P WC)", "entry"),
        ],
        "La cintura se corrige con el pliegue abdominal.",
    ),
]

GRUPOS_DERECHA = [
    (
        "Masa cutánea (piel)",
        [],
        "No requiere medidas extra: se calcula con peso, talla, sexo y edad "
        "(superficie de DuBois). MS = SA x TSK x 1,05.",
    ),
    (
        "Masa muscular: 5 perímetros (cm)",
        [
            ("brazo_relajado", "Brazo relajado (P ARC)", "entry"),
            ("antebrazo", "Antebrazo máximo (P FA)", "entry"),
            ("torax_mesoesternal", "Tórax mesoesternal (P CHC)", "entry"),
            ("muslo_superior", "Muslo superior (P THC)", "entry"),
            ("pierna_maximo", "Pantorrilla máxima (P MCC)", "entry"),
        ],
        "El antebrazo no se corrige; el resto se corrige con su pliegue.",
    ),
    (
        "Masa ósea: diámetros y cabeza (cm)",
        [
            ("cabeza", "Perímetro de cabeza", "entry"),
            ("biacromial", "Biacromial (BIAC)", "entry"),
            ("biiliocrestal", "Biiliocrestal (BIIL)", "entry"),
            ("humero", "Húmero (HUM)", "entry"),
            ("femur", "Fémur (FEM)", "entry"),
        ],
        None,
    ),
]

ISAK_MAP = {
    "peso": "masa_corporal",
    "estatura": "estatura",
    "talla_sentado": "talla_sentado",
    "triceps": "triceps",
    "subescapular": "subescapular",
    "supraespinal": "supraespinal",
    "abdominal": "abdominal",
    "muslo_anterior": "muslo_anterior",
    "pierna_medial": "pierna_medial",
    "brazo_relajado": "brazo_relajado",
    "antebrazo": "antebrazo",
    "torax_mesoesternal": "torax_mesoesternal",
    "muslo_superior": "muslo_1cm_gluteo",
    "pierna_maximo": "pierna_maximo",
    "cabeza": "cabeza",
    "biacromial": "biacromial",
    "biiliocrestal": "biiliocrestal",
    "humero": "humero",
    "femur": "femur",
    "cintura": "cintura",
    "torax_ap": "torax_ap",
    "torax_transverso": "torax_transverso",
}

# Medidas que pueden venir del registro antropométrico (no del perfil ISAK).
ORIGEN_ANTROPOMETRIA = {"peso": "peso", "estatura": "altura"}

EQUIVALENCIAS = [
    ("Peso (kg)", "Antropometría: Peso", "ISAK: Masa corporal", "Mismo dato"),
    ("Talla (HT)", "Antropometría: Altura", "ISAK: Estatura", "Mismo dato"),
    ("Talla sentado (SIT HT)", "—", "ISAK: Talla sentado", "Solo perfil ISAK"),
    ("Pliegue tricipital (TPSF)", "—", "ISAK: Tríceps", "Mismo dato"),
    ("Pliegue subescapular (SSSF)", "—", "ISAK: Subescapular", "Mismo dato"),
    ("Pliegue supraespinal (SISF)", "—", "ISAK: Supraespinal", "Mismo dato"),
    ("Pliegue abdominal (ABSF)", "—", "ISAK: Abdominal", "Mismo dato"),
    (
        "Pliegue del muslo frontal (THSF)",
        "—",
        "ISAK: Muslo anterior",
        "Muslo medial / anterior / frontal: mismo punto",
    ),
    (
        "Pliegue pantorrilla medial (MCSF)",
        "—",
        "ISAK: Pierna medial",
        "Pantorrilla medial = pierna medial",
    ),
    ("Brazo relajado (P ARC)", "—", "ISAK: Brazo relajado", "Se corrige con tríceps"),
    ("Antebrazo máximo (P FA)", "—", "ISAK: Antebrazo (máximo)", "No se corrige"),
    (
        "Caja torácica (P CHC)",
        "—",
        "ISAK: Tórax (mesoesternal)",
        "Se corrige con subescapular",
    ),
    (
        "Muslo superior (P THC)",
        "—",
        "ISAK: Muslo (1 cm glúteo)",
        "No confundir con muslo medio",
    ),
    (
        "Pantorrilla máxima (P MCC)",
        "—",
        "ISAK: Pierna (máximo)",
        "Se corrige con pierna medial",
    ),
    ("Perímetro cefálico", "—", "ISAK: Cabeza", "Masa ósea de la cabeza"),
    ("Biacromial (BIAC)", "—", "ISAK: Biacromial", "Mismo dato"),
    ("Biiliocrestal (BIIL)", "—", "ISAK: Biiliocrestal", "Mismo dato"),
    ("Húmero (HUM)", "—", "ISAK: Húmero", "Diámetro biepicondilar"),
    ("Fémur (FEM)", "—", "ISAK: Fémur", "Diámetro bicondilar"),
    ("Cintura (P WC)", "—", "ISAK: Cintura (mínima)", "Se corrige con abdominal"),
    ("Tórax A-P (D APCH)", "—", "ISAK: Tórax A-P", "Mismo dato"),
    ("Tórax transverso (D TRCH)", "—", "ISAK: Tórax transverso", "Mismo dato"),
]


class Componentes5Tab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self._paciente_cargado = None
        self.campos = {}
        self.etiquetas = {}

    # ------------------------------------------------------------------
    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  🧬 5 Componentes  ")

        titulo = tk.Label(
            self.marco,
            text="FRACCIONAMIENTO ANTROPOMÉTRICO EN 5 COMPONENTES",
            font=("Impact", 18),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 2))

        tk.Label(
            self.marco,
            text="Ross & Kerr (1993) / Kerr (1988): piel, tejido adiposo, "
            "músculo, hueso y tejido residual.  Toma peso y altura de "
            "Antropometría y el resto del perfil ISAK.",
            font=("Segoe UI", 9),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(fill="x")

        self.lbl_estado = ttk.Label(
            self.marco,
            text="5 Componentes: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 2))

        barra = ttk.Frame(self.marco, style="Gym.TFrame")
        barra.pack(fill="x", padx=8, pady=(2, 4))
        for i, (texto, comando, primario) in enumerate(
            [
                ("CARGAR DESDE ANTROPOMETRÍA", self.cargar_medidas, True),
                ("VER EQUIVALENCIAS", self.ver_equivalencias, False),
                ("CALCULAR", self.calcular, False),
                ("IMPRIMIR", self.imprimir, False),
                ("LIMPIAR", self.limpiar, False),
            ]
        ):
            tk.Button(
                barra,
                text=texto,
                command=comando,
                font=("Impact", 11),
                fg=NEGRO if primario else NEON,
                bg=NEON if primario else GRIS,
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=12,
                pady=5,
                cursor="hand2",
            ).pack(side="left", padx=(0, 6))

        paned = ttk.PanedWindow(self.marco, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._crear_panel_medidas(paned)
        self._crear_panel_resultados(paned)

    # ------------------------------------------------------------------
    def _crear_panel_medidas(self, paned):
        contenedor = ttk.LabelFrame(paned, text="Medidas requeridas", padding=4)
        paned.add(contenedor, weight=3)

        canvas = tk.Canvas(
            contenedor, bg=GRIS_OSCURO, highlightthickness=0
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
        interior.columnconfigure(0, weight=1)
        interior.columnconfigure(1, weight=1)

        self._crear_columna(interior, 0, GRUPOS_IZQUIERDA)
        self._crear_columna(interior, 1, GRUPOS_DERECHA)

    def _crear_columna(self, interior, columna, grupos):
        for fila, (titulo, campos, nota) in enumerate(grupos):
            marco = ttk.LabelFrame(interior, text=titulo, padding=5)
            marco.grid(
                row=fila, column=columna, sticky="new", padx=4, pady=4
            )
            marco.columnconfigure(1, weight=1)

            base = 0
            if nota:
                ttk.Label(
                    marco,
                    text=nota,
                    style="Gym.TLabel",
                    wraplength=250,
                    justify="left",
                ).grid(
                    row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)
                )
                base = 1

            for i, (clave, etiqueta, tipo) in enumerate(campos):
                self.etiquetas[clave] = etiqueta
                ttk.Label(
                    marco, text="{etiqueta}:", style="Gym.TLabel"
                ).grid(
                    row=base + i,
                    column=0,
                    sticky="e",
                    padx=(2, 4),
                    pady=3,
                )
                if tipo == "combo":
                    widget = ttk.Combobox(
                        marco,
                        values=["Mujer", "Hombre"],
                        state="readonly",
                        width=10,
                        style="Gym.TCombobox",
                    )
                    widget.set("Mujer")
                else:
                    widget = ttk.Entry(
                        marco, width=12, style="Gym.TEntry"
                    )
                widget.grid(
                    row=base + i,
                    column=1,
                    sticky="w",
                    padx=(0, 4),
                    pady=3,
                )
                self.campos[clave] = widget

    # ------------------------------------------------------------------
    def _crear_panel_resultados(self, paned):
        marco = ttk.LabelFrame(paned, text="Resultado", padding=6)
        paned.add(marco, weight=2)

        ttk.Label(marco, text="5 COMPONENTES", style="Estado.TLabel").pack(
            anchor="w"
        )

        self.tabla = ttk.Treeview(
            marco,
            columns=("componente", "kg", "pct"),
            show="headings",
            height=7,
            style="Gym.Treeview",
        )
        for col, texto, ancho, anchor in (
            ("componente", "Componente", 150, "w"),
            ("kg", "kg", 65, "e"),
            ("pct", "% total", 65, "e"),
        ):
            self.tabla.heading(col, text=texto)
            self.tabla.column(col, width=ancho, anchor=anchor)
        self.tabla.pack(fill="x", pady=(4, 6))
        self.tabla.tag_configure("total", background=GRIS)

        ttk.Label(marco, text="RESUMEN", style="Estado.TLabel").pack(
            anchor="w", pady=(4, 0)
        )
        self.lbl_resumen = tk.Label(
            marco,
            text="Captura las medidas y pulsa CALCULAR.",
            bg=GRIS_OSCURO,
            fg=BLANCO,
            justify="left",
            anchor="w",
            font=("Consolas", 10),
            padx=4,
            pady=4,
        )
        self.lbl_resumen.pack(fill="x")

        ttk.Label(marco, text="DETALLE DEL CÁLCULO", style="Estado.TLabel").pack(
            anchor="w", pady=(6, 0)
        )
        self.lbl_detalle = tk.Label(
            marco,
            text="",
            bg=GRIS_OSCURO,
            fg=GRIS_TEXTO,
            justify="left",
            anchor="nw",
            font=("Consolas", 9),
            wraplength=350,
            padx=4,
            pady=4,
        )
        self.lbl_detalle.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def ver_equivalencias(self):
        ventana = tk.Toplevel(self.marco)
        ventana.title("Equivalencias de medidas")
        ventana.configure(bg=GRIS_OSCURO)
        ventana.geometry("880x540")
        ventana.transient(self.marco.winfo_toplevel())

        tk.Label(
            ventana,
            text="MISMA MEDIDA, DISTINTOS NOMBRES",
            font=("Impact", 18),
            fg=NEON,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(
            ventana,
            text="Nombre en el método FA5C  ->  nombre en este proyecto / ISAK",
            font=("Segoe UI", 9),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12)

        contenedor = ttk.Frame(ventana, style="Gym.TFrame")
        contenedor.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        tabla = ttk.Treeview(
            contenedor,
            columns=("fa5c", "proyecto", "isak", "nota"),
            show="headings",
            height=16,
            style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("fa5c", "Medida FA5C", 240),
            ("proyecto", "Antropometría", 190),
            ("isak", "Perfil ISAK", 190),
            ("nota", "Observación", 220),
        ):
            tabla.heading(col, text=texto)
            tabla.column(col, width=ancho, anchor="w")

        scroll = ttk.Scrollbar(
            contenedor, orient="vertical", command=tabla.yview
        )
        tabla.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tabla.pack(side="left", fill="both", expand=True)

        for fila in EQUIVALENCIAS:
            tabla.insert("", "end", values=fila)

        tk.Label(
            ventana,
            text="Nota: el método usa el muslo superior (1 cm bajo el pliegue "
            "glúteo), no el muslo medio. El pliegue del muslo aparece como "
            "medial, anterior o frontal: es el mismo sitio.",
            font=("Segoe UI", 9),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
            justify="left",
            wraplength=840,
        ).pack(anchor="w", padx=12, pady=(0, 10))

    # ------------------------------------------------------------------
    def _set_valor(self, clave, texto):
        widget = self.campos.get(clave)
        if widget is None:
            return
        if isinstance(widget, ttk.Combobox):
            widget.set(texto)
            return
        widget.delete(0, "end")
        widget.insert(0, texto)

    def _get_valor(self, clave):
        widget = self.campos.get(clave)
        return widget.get().strip() if widget is not None else ""

    @staticmethod
    def _valor_isak(valores):
        if not valores:
            return None
        if len(valores) == 1:
            return valores[0]
        if len(valores) == 2:
            return (valores[0] + valores[1]) / 2.0
        return sorted(valores)[1]

    def _sexo_paciente(self, paciente):
        genero = str(paciente.get("genero") or "").strip().lower()
        if genero.startswith("m") and not genero.startswith("mu"):
            return "Hombre"
        if genero.startswith("h"):
            return "Hombre"
        if genero.startswith("f") or genero.startswith("mu"):
            return "Mujer"
        return "Mujer"

    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        self.lbl_estado.configure(
            text="5 Componentes del paciente {paciente_id}"
        )
        if paciente_id != self._paciente_cargado and not self._hay_datos():
            self.cargar_medidas(silencioso=True)

    def refrescar_estado(self):
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            return
        if paciente_id != self.paciente_id:
            self.cargar(paciente_id)
        elif not self._hay_datos():
            self.cargar_medidas(silencioso=True)

    def _hay_datos(self):
        for clave in self.campos:
            if clave in {"sexo", "edad"}:
                continue
            if self._get_valor(clave):
                return True
        return False

    def _limpiar_widgets(self):
        for clave, widget in self.campos.items():
            if isinstance(widget, ttk.Combobox):
                widget.set("Mujer")
            else:
                widget.delete(0, "end")
        self._set_valor("edad", "18")
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        self.lbl_resumen.configure(
            text="Captura las medidas y pulsa CALCULAR."
        )
        self.lbl_detalle.configure(text="")

    def limpiar(self):
        self._limpiar_widgets()
        self._paciente_cargado = None

    def desvincular(self):
        self.paciente_id = None
        self._paciente_cargado = None
        self._limpiar_widgets()
        self.lbl_estado.configure(
            text="5 Componentes: sin paciente seleccionado"
        )

    # ------------------------------------------------------------------
    def cargar_medidas(self, silencioso=False):
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            if not silencioso:
                messagebox.showwarning(
                    "5 Componentes",
                    "Selecciona un paciente antes de cargar medidas.",
                )
            return False

        avisos = []
        cargados = 0

        paciente = database.obtener_paciente(paciente_id) or {}
        self.paciente_id = paciente_id
        self._set_valor("sexo", self._sexo_paciente(paciente))
        edad = calcular_edad(
            paciente.get("fecha_nacimiento") or paciente.get("dob")
        )
        if edad is not None:
            self._set_valor("edad", str(edad))
        else:
            self._set_valor("edad", "18")
            avisos.append(
                "No se pudo calcular la edad; se usaron 18 años para la "
                "superficie corporal."
            )

        # --- Peso y altura desde el registro de antropometría ---
        filas = database.obtener_antropometria()
        fila = next(
            (f for f in filas if f["paciente_id"] == paciente_id), None
        )
        for clave, columna in ORIGEN_ANTROPOMETRIA.items():
            if fila is None:
                continue
            texto = str(fila[columna] or "").strip().replace(",", ".")
            if not texto:
                continue
            try:
                float(texto)
            except ValueError:
                avisos.append(
                    "El dato de {self.etiquetas[clave]} en antropometría "
                    "no es numérico."
                )
                continue
            self._set_valor(clave, texto)
            cargados += 1
        if fila is None:
            avisos.append("El paciente no tiene antropometría guardada.")

        # --- Resto de medidas desde el perfil ISAK más reciente ---
        registros = database.obtener_perfil_isak(paciente_id)
        if not registros:
            avisos.append("El paciente no tiene perfil ISAK guardado.")
        else:
            datos = json.loads(registros[0]["datos"])
            faltantes_isak = []
            for clave, origen in ISAK_MAP.items():
                if clave in ORIGEN_ANTROPOMETRIA and self._get_valor(clave):
                    continue
                valores = []
                for i in (1, 2, 3):
                    texto = (
                        str(datos.get("{origen}_{i}") or "")
                        .strip()
                        .replace(",", ".")
                    )
                    if not texto:
                        continue
                    try:
                        valores.append(float(texto))
                    except ValueError:
                        continue
                final = self._valor_isak(valores)
                if final is None:
                    faltantes_isak.append(self.etiquetas[clave])
                    continue
                self._set_valor(clave, "{final:.6g}")
                cargados += 1
            if faltantes_isak:
                avisos.append(
                    "Sin dato en el perfil ISAK: "
                    + ", ".join(faltantes_isak)
                )

        self._paciente_cargado = paciente_id
        self.lbl_estado.configure(
            text="5 Componentes del paciente {paciente_id}"
        )

        if silencioso:
            return cargados > 0
        if avisos:
            messagebox.showinfo(
                "5 Componentes",
                "Medidas cargadas: "
                "{cargados}.\n\n" + "\n".join(avisos),
            )
        else:
            messagebox.showinfo(
                "5 Componentes",
                "Se cargaron {cargados} medidas desde Antropometría e ISAK.",
            )
        return cargados > 0

    # ------------------------------------------------------------------
    def _leer_numeros(self):
        datos = {}
        faltantes = []
        invalidos = []
        for clave, widget in self.campos.items():
            if clave == "sexo":
                continue
            texto = self._get_valor(clave).replace(",", ".")
            etiqueta = self.etiquetas[clave]
            if not texto:
                faltantes.append(etiqueta)
                continue
            try:
                datos[clave] = float(texto)
            except ValueError:
                invalidos.append(etiqueta)
        return datos, faltantes, invalidos

    def calcular(self):
        datos, faltantes, invalidos = self._leer_numeros()
        datos["sexo"] = self._get_valor("sexo") or "Mujer"
        if faltantes:
            messagebox.showwarning(
                "Validación",
                "Faltan medidas de: " + ", ".join(faltantes) + ".",
            )
            return
        if invalidos:
            messagebox.showwarning(
                "Validación",
                "Valor no numérico en: " + ", ".join(invalidos) + ".",
            )
            return

        if datos["peso"] <= 0 or datos["estatura"] <= 0:
            messagebox.showwarning(
                "Validación", "El peso y la talla deben ser mayores que cero."
            )
            return
        if datos["talla_sentado"] <= 0:
            messagebox.showwarning(
                "Validación", "La talla sentado debe ser mayor que cero."
            )
            return
        if datos["edad"] <= 0:
            messagebox.showwarning(
                "Validación", "La edad debe ser mayor que cero."
            )
            return

        pesos = [
            datos["triceps"],
            datos["subescapular"],
            datos["supraespinal"],
            datos["abdominal"],
            datos["muslo_anterior"],
            datos["pierna_medial"],
        ]
        if any(valor <= 0 for valor in pesos):
            messagebox.showwarning(
                "Validación",
                "Los seis pliegues cutáneos deben ser mayores que cero.",
            )
            return

        resultado = self._calcular_componentes(datos)
        self._resultado_actual = resultado
        self._mostrar_resultado(resultado)

    @staticmethod
    def _calcular_componentes(datos):
        peso = datos["peso"]
        estatura = datos["estatura"]
        talla_sentado = datos["talla_sentado"]
        edad = datos["edad"]
        sexo = datos["sexo"].strip().lower()
        mujer = sexo.startswith("mu") or sexo.startswith("f")

        if edad < 12:
            csa = 70.691
        elif mujer:
            csa = 73.704
        else:
            csa = 68.308
        tsk = 1.96 if mujer else 2.07

        superficie = (
            csa * peso ** 0.425 * estatura ** 0.725 / 10000.0
        )
        piel = superficie * tsk * 1.05

        ratio = ALTURA_PHANTOM / estatura

        suma_adiposa = (
            datos["triceps"]
            + datos["subescapular"]
            + datos["supraespinal"]
            + datos["abdominal"]
            + datos["muslo_anterior"]
            + datos["pierna_medial"]
        )
        z_adiposa = (suma_adiposa * ratio - 116.41) / 34.79
        adiposa = (z_adiposa * 5.85 + 25.6) / ratio ** 3

        brazo_corr = datos["brazo_relajado"] - math.pi * datos["triceps"] / 10.0
        antebrazo = datos["antebrazo"]
        torax_corr = (
            datos["torax_mesoesternal"]
            - math.pi * datos["subescapular"] / 10.0
        )
        muslo_corr = (
            datos["muslo_superior"]
            - math.pi * datos["muslo_anterior"] / 10.0
        )
        pantorrilla_corr = (
            datos["pierna_maximo"]
            - math.pi * datos["pierna_medial"] / 10.0
        )
        suma_muscular = (
            brazo_corr + antebrazo + torax_corr + muslo_corr + pantorrilla_corr
        )
        z_muscular = (suma_muscular * ratio - 207.21) / 13.74
        muscular = (z_muscular * 5.4 + 24.5) / ratio ** 3

        z_osea_cabeza = (datos["cabeza"] - 56.0) / 1.44
        osea_cabeza = z_osea_cabeza * 0.18 + 1.20
        suma_osea = (
            datos["biacromial"]
            + datos["biiliocrestal"]
            + 2 * datos["humero"]
            + 2 * datos["femur"]
        )
        z_osea_cuerpo = (suma_osea * ratio - 98.88) / 5.33
        osea_cuerpo = (z_osea_cuerpo * 1.34 + 6.70) / ratio ** 3
        osea = osea_cabeza + osea_cuerpo

        cintura_corr = datos["cintura"] - math.pi * datos["abdominal"] / 10.0
        suma_residual = datos["torax_ap"] + datos["torax_transverso"] + cintura_corr
        ratio_sentado = ALTURA_SENTADO_PHANTOM / talla_sentado
        z_residual = (suma_residual * ratio_sentado - 109.35) / 7.08
        residual = (z_residual * 1.24 + 6.10) / ratio_sentado ** 3

        total = piel + adiposa + muscular + osea + residual

        return {
            "piel": piel,
            "adiposa": adiposa,
            "muscular": muscular,
            "osea": osea,
            "residual": residual,
            "total": total,
            "peso": peso,
            "estatura": estatura,
            "superficie": superficie,
            "suma_adiposa": suma_adiposa,
            "suma_muscular": suma_muscular,
            "suma_osea": suma_osea,
            "suma_residual": suma_residual,
            "brazo_corr": brazo_corr,
            "torax_corr": torax_corr,
            "muslo_corr": muslo_corr,
            "pantorrilla_corr": pantorrilla_corr,
            "cintura_corr": cintura_corr,
            "z_adiposa": z_adiposa,
            "z_muscular": z_muscular,
            "z_osea_cabeza": z_osea_cabeza,
            "z_osea_cuerpo": z_osea_cuerpo,
            "z_residual": z_residual,
            "osea_cabeza": osea_cabeza,
            "osea_cuerpo": osea_cuerpo,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _clasificar_imc(imc):
        if imc < 18.5:
            return "bajo peso"
        if imc < 25.0:
            return "normal"
        if imc < 30.0:
            return "sobrepeso"
        return "obesidad"

    def _mostrar_resultado(self, res):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)

        total = res["total"] or 1.0
        componentes = [
            ("Piel (cutánea)", res["piel"]),
            ("Tejido adiposo", res["adiposa"]),
            ("Músculo", res["muscular"]),
            ("Hueso", res["osea"]),
            ("Tejido residual", res["residual"]),
        ]
        for nombre, valor in componentes:
            self.tabla.insert(
                "",
                "end",
                values=(nombre, "{valor:.2f}", "{100 * valor / total:.1f}"),
            )
        self.tabla.insert(
            "",
            "end",
            values=("Total predictivo", "{total:.2f}", "100.0"),
            tags=("total",),
        )

        imc = res["peso"] / (res["estatura"] / 100.0) ** 2
        imo = res["muscular"] / res["osea"] if res["osea"] else 0.0
        diferencia = total - res["peso"]
        diferencia_pct = 100 * diferencia / res["peso"] if res["peso"] else 0.0

        self.lbl_resumen.configure(
            text=(
                "Peso real:        {res['peso']:.2f} kg\n"
                "Masa predictiva:  {total:.2f} kg\n"
                "Diferencia:       {diferencia:+.2f} kg "
                "({diferencia_pct:+.1f} %)\n"
                "IMC:              {imc:.1f} kg/m² "
                "({self._clasificar_imc(imc)})\n"
                "IMO (músculo/óseo): {imo:.2f}"
            )
        )

        self.lbl_detalle.configure(
            text=(
                "Superficie corporal: {res['superficie']:.3f} m²\n"
                "Σ 6 pliegues: {res['suma_adiposa']:.1f} mm\n"
                "Σ 5 perímetros corregidos: {res['suma_muscular']:.1f} cm\n"
                "   brazo {res['brazo_corr']:.1f} · tórax "
                "{res['torax_corr']:.1f} · muslo {res['muslo_corr']:.1f} · "
                "pantorrilla {res['pantorrilla_corr']:.1f}\n"
                "Σ diámetros óseos: {res['suma_osea']:.1f} cm\n"
                "   ósea cabeza {res['osea_cabeza']:.2f} kg · cuerpo "
                "{res['osea_cuerpo']:.2f} kg\n"
                "Σ residual: {res['suma_residual']:.1f} cm "
                "(cintura corr. {res['cintura_corr']:.1f})\n\n"
                "Z Phantom (proporcionalidad)\n"
                "   adiposo {res['z_adiposa']:+.2f} · muscular "
                "{res['z_muscular']:+.2f}\n"
                "   óseo cuerpo {res['z_osea_cuerpo']:+.2f} · "
                "óseo cabeza {res['z_osea_cabeza']:+.2f}\n"
                "   residual {res['z_residual']:+.2f}"
            )
        )

    def imprimir(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "5 Componentes", "Selecciona un paciente antes de imprimir."
            )
            return
        res = getattr(self, "_resultado_actual", None)
        if res is None:
            messagebox.showwarning(
                "5 Componentes", "Calcula los 5 componentes antes de imprimir."
            )
            return
        paciente = database.obtener_paciente(self.paciente_id) or {}
        nombre = paciente.get("nombre") or "paciente_{self.paciente_id}"
        ruta = antropometria_print.ruta_temporal_pdf_componentes(nombre)
        try:
            medidas = [
                ("Peso", self._get_valor("peso") or res.get("peso")),
                ("Talla / estatura", self._get_valor("estatura") or res.get("estatura")),
                ("Talla sentado", self._get_valor("talla_sentado")),
                ("Sexo", self._get_valor("sexo") or paciente.get("genero") or "-"),
                ("Edad", self._get_valor("edad")),
                ("Tr?ceps", self._get_valor("triceps")),
                ("Subescapular", self._get_valor("subescapular")),
                ("Supraespinal", self._get_valor("supraespinal")),
                ("Abdominal", self._get_valor("abdominal")),
                ("Muslo anterior", self._get_valor("muslo_anterior")),
                ("Pierna medial", self._get_valor("pierna_medial")),
                ("Brazo relajado", self._get_valor("brazo_relajado")),
                ("Antebrazo", self._get_valor("antebrazo")),
                ("T?rax mesoesternal", self._get_valor("torax_mesoesternal")),
                ("Muslo superior", self._get_valor("muslo_superior")),
                ("Pantorrilla m?xima", self._get_valor("pierna_maximo")),
                ("Cabeza", self._get_valor("cabeza")),
                ("Biacromial", self._get_valor("biacromial")),
                ("Biiliocrestal", self._get_valor("biiliocrestal")),
                ("H?mero", self._get_valor("humero")),
                ("F?mur", self._get_valor("femur")),
                ("Cintura", self._get_valor("cintura")),
                ("T?rax A-P", self._get_valor("torax_ap")),
                ("T?rax transverso", self._get_valor("torax_transverso")),
            ]
            salida = dict(res)
            salida["medidas"] = medidas
            salida["talla_sentado"] = self._get_valor("talla_sentado") or res.get("talla_sentado")
            antropometria_print.generar_pdf_componentes(ruta, paciente, salida)
        except Exception as error:
            messagebox.showerror(
                "Imprimir", "No se pudo generar el reporte:\n" + str(error)
            )
            return
        try:
            antropometria_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                "Se generó el PDF en:\n" + str(ruta) + "\n\n"
                "No se pudo abrir automáticamente: " + str(error),
            )
            return
        messagebox.showinfo(
            "Imprimir",
            "Reporte generado:\n" + str(ruta) + "\n\nIncluye membrete, datos del paciente, 5 componentes, índices y medidas.",
        )
