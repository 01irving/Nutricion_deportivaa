import io
import json
import os
import unicodedata
import tkinter as tk
from tkinter import messagebox, ttk

try:  # Tk nativo solo decodifica PNG/GIF; Pillow permite leer el JPEG guardado en la BD
    from PIL import Image, ImageTk
except Exception:  # pragma: no cover - entorno sin Pillow
    Image = None
    ImageTk = None

import calentamiento_print
import database
import estiramientos_print
import rutina_print
from estiramientos_tab import DURACIONES, MOMENTOS
from rutas import base_dir

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

RUTA_IMAGENES = os.path.join(base_dir(), "assets", "rutinas")
CATALOGOS_JSON = {
    "hombros": "hombros_ejercicios.json",
    "brazos": "brazos_ejercicios.json",
    "piernas": "piernas_ejercicios.json",
    "espalda": "espalda_ejercicios.json",
    "gluteos": "gluteos_ejercicios.json",
    "pectorales": "pectorales_ejercicios.json",
    "abdominales": "abdominales_ejercicios.json",
}
GRUPOS_PREFERIDOS = ("hombros", "brazos", "pectorales", "espalda", "piernas", "gluteos", "abdominales")
GRUPOS_ETIQUETAS = {"gluteos": "Glúteos"}

TAMANO_IMG_RESPALDO = (560, 380)

# Porcentajes del 1RM ofrecidos para llenar el peso (discos de 2.5 kg)
PORCENTAJES_1RM = tuple(range(50, 101, 5))

# Días de la rutina semanal (mismo orden que la pestaña Menús)
DIAS_SEMANA = (
    "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo",
)


def _discos_2_5(kg):
    """Redondea al disco cargable más cercano (múltiplos de 2.5 kg)."""
    return round(kg / 2.5) * 2.5


def _normalizar(texto):
    """Minúsculas y sin acentos, para emparejar nombres de ejercicios."""
    texto = (texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")

# ----------------------------------------------------------------------
# Pestaña Progresión — Position Stand del ACSM: "Progression Models in
# Resistance Training for Healthy Adults" (Med Sci Sports Exerc,
# 2009;41(3):687-708). Tres ramas: principiantes, intermedios, avanzados.
# ----------------------------------------------------------------------
CONTENIDO_INTRO_PROGRESION = """TITULO: MODELO DE PROGRESIÓN (ACSM 2009)

Elige tu nivel en el árbol de la izquierda.

◆ Principiantes — sin experiencia o desentrenados por años
◆ Intermedios — alrededor de 6 meses de entrenamiento constante
◆ Avanzados — años de entrenamiento con cargas

Regla que atraviesa todos los niveles: cuando el atleta complete
1-2 repeticiones más que las objetivo con su carga actual, se
aumenta el peso entre 2% y 10%.
"""

CONTENIDO_PROGRESION = {
    "principiantes": """TITULO: 🟢 PRINCIPIANTES

Sin experiencia en pesas o desentrenados durante varios años.

◆ Frecuencia
2-3 días por semana, entrenando cada grupo muscular en cada
sesión (rutina de cuerpo completo).

◆ Carga y repeticiones
Cargas que permitan 8-12 repeticiones máximas (RM) por
ejercicio.

◆ Series
1-3 series por ejercicio; empezar conservador y sumar series
según se adapte.

◆ Velocidad de ejecución
Moderada: 1-2 segundos la fase concéntrica (subida) y 1-2
segundos la excéntrica (bajada).

◆ Descanso
1-2 minutos entre series; 2-3 minutos en multiarticulares
pesadas.

◆ Selección de ejercicios
Multiarticulares antes que unilaterales; grandes grupos
musculares antes que los pequeños.

◆ Progresión
Al completar 1-2 repeticiones por encima del rango objetivo,
aumentar la carga 2-10%.
""",
    "intermedios": """TITULO: 🟡 INTERMEDIOS

Alrededor de 6 meses de entrenamiento de fuerza constante.

◆ Frecuencia
3-4 días por semana.

◆ Carga y repeticiones
Rango más amplio: 1-12 RM usado EN FORMA PERIODIZADA, con
énfasis en cargas pesadas (1-6 RM).

◆ Series
Múltiples series por ejercicio; variar el volumen por ciclos.

◆ Velocidad de ejecución
Moderada: 1-2 segundos concéntrico, 1-2 segundos excéntrico.

◆ Descanso
3-5 minutos entre series con cargas pesadas multiarticulares;
1-2 minutos si el objetivo de la serie es hipertrofia.

◆ Periodización
Entrenar en forma periodizada (lineal u ondulante): alternar
bloques de volumen e intensidad para seguir progresando.

◆ Progresión
2-10% de aumento de carga al superar el rango objetivo;
manipular también series y frecuencia entre microciclos.
""",
    "avanzados": """TITULO: 🔴 AVANZADOS

Años de entrenamiento de fuerza sistemático.

◆ Frecuencia
4-5 días por semana (rutinas divididas por grupos musculares).

◆ Carga y repeticiones
1-12 RM periodizado, progresando con énfasis hacia 1-6 RM.

◆ Series y volumen
Alto volumen planificado: múltiples series y ejercicios por
grupo, manipulados por mesociclo.

◆ Velocidad de ejecución
Moderada para fuerza; para potencia, cargas ligeras movidas a
máxima velocidad: 0-60% de 1RM en tren inferior y 30-60% de
1RM en tren superior, 3-5 series por ejercicio.

◆ Descanso
3-5 minutos entre series pesadas y de potencia.

◆ Periodización
Plan anual completo: macrociclo, mesociclos y microciclos,
alternando fuerza, potencia y picos.

◆ Progresión
Además del 2-10% de carga, progresar manipulando volumen,
intensidad, frecuencia y descansos; incluir acciones
concéntricas, excéntricas e isométricas, trabajo bilateral y
unilateral.
""",
}

REGLAS_GENERALES_PROGRESION = (
    "Reglas generales (todos los niveles): sube la carga 2-10% al "
    "completar 1-2 reps más que el objetivo · grandes músculos antes "
    "que pequeños y multiarticulares antes que unilaterales · "
    "hipertrofia: 6-12 RM con 1-2 min de descanso y varias series · "
    "resistencia muscular: 40-60% de 1RM, >15 reps, descanso <90 s · "
    "potencia: cargas ligeras a máxima velocidad con 3-5 min de "
    "descanso · intermedios y avanzados entrenan en forma periodizada."
)


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
        # último 1RM calculado en el diálogo (cualquier método) y lista
        # de referencias 1RM para llenar el peso por porcentaje
        self.rm_sesion = None
        self._rm_lista = []
        # día de la semana que se está editando de la rutina semanal
        self.dia_actual = DIAS_SEMANA[0]
        self.dia_buttons = {}

    def _abrir_1rm(self):
        """Calculadora de 1RM por ejercicio (ramas de árbol)."""
        import calculadora_1rm

        resultado = calculadora_1rm.abrir_dialogo_1rm(self.marco, self.app)
        if resultado:
            self.rm_sesion = resultado
        self._recargar_referencias_1rm()
        if resultado:
            self._mensaje(
                f"1RM activo: {resultado['ejercicio']} {resultado['resultado']} kg"
            )

    # ------------------------------------------------------------------
    # Peso desde el 1RM: referencias de la sesión y las guardadas
    # ------------------------------------------------------------------

    def _recargar_referencias_1rm(self):
        """Llena el combo "1RM de referencia": el último calculado en la
        sesión y los guardados del paciente activo; preselecciona el del
        ejercicio mostrado."""
        if not hasattr(self, "combo_rm_ref"):
            return
        referencias = []
        if self.rm_sesion:
            referencias.append(
                {
                    "rm": self.rm_sesion.get("resultado") or 0,
                    "ejercicio": self.rm_sesion.get("ejercicio") or "",
                    "etiqueta": (
                        f"Sesión · {self.rm_sesion['ejercicio']} — "
                        f"{self.rm_sesion['resultado']:g} kg"
                    ),
                }
            )
        paciente_id = self._paciente_actual()
        if paciente_id is not None:
            try:
                registros = database.get_uno_rm(paciente_id)
            except Exception:
                registros = []
            for reg in registros:
                if not reg.get("resultado"):
                    continue
                # la fecha se guarda AAAA-MM-DD y se muestra DD/MM/AAAA
                fecha = str(reg.get("fecha") or "—")
                try:
                    if fecha != "—":
                        fecha = f"{fecha[8:10]}/{fecha[5:7]}/{fecha[0:4]}"
                except Exception:
                    pass
                referencias.append(
                    {
                        "rm": reg["resultado"],
                        "ejercicio": reg.get("ejercicio") or "",
                        "etiqueta": (
                            f"{fecha} · {reg.get('ejercicio')} — "
                            f"{reg['resultado']:g} kg"
                        ),
                    }
                )
        self._rm_lista = referencias
        self.combo_rm_ref.configure(values=[r["etiqueta"] for r in referencias])

        # preselección: el 1RM del ejercicio mostrado o la primera referencia
        self.combo_rm_ref.set(self._buscar_ref_ejercicio() or (referencias[0]["etiqueta"] if referencias else ""))
        self._llenar_pct_1rm()

    def _buscar_ref_ejercicio(self):
        """Etiqueta de la primera referencia 1RM cuyo ejercicio coincida
        (ignorando mayúsculas y acentos) con el ejercicio mostrado."""
        nombre = _normalizar((self.ejercicio_seleccionado or {}).get("nombre"))
        if not nombre:
            return None
        for ref in self._rm_lista:
            if _normalizar(ref.get("ejercicio")) == nombre:
                return ref["etiqueta"]
        return None

    def _rm_actual(self):
        """Referencia 1RM elegida en el combo (None si no hay ninguna)."""
        texto = self.combo_rm_ref.get()
        for ref in self._rm_lista:
            if ref["etiqueta"] == texto:
                return ref
        return None

    def _llenar_pct_1rm(self):
        """Porcentajes del 1RM elegido con el peso ya calculado y
        redondeado a discos de 2.5 kg."""
        self.combo_rm_pct.set("")
        ref = self._rm_actual()
        if not ref or not ref.get("rm"):
            self.combo_rm_pct.configure(values=[])
            return
        self.combo_rm_pct.configure(
            values=[
                f"{pct}% → {_discos_2_5(ref['rm'] * pct / 100.0):g} kg"
                for pct in PORCENTAJES_1RM
            ]
        )

    def _al_elegir_rm_ref(self, event=None):
        self._llenar_pct_1rm()

    def _al_elegir_pct_1rm(self, event=None):
        """Pone en "Peso (kg)" el porcentaje elegido del 1RM de
        referencia, redondeado al disco cargable más cercano."""
        ref = self._rm_actual()
        if not ref or not ref.get("rm"):
            return
        try:
            pct = float(self.combo_rm_pct.get().split("%", 1)[0])
        except ValueError:
            return
        exacto = ref["rm"] * pct / 100.0
        carga = _discos_2_5(exacto)
        entrada = self.reg_entradas["Peso (kg)"]
        entrada.delete(0, "end")
        entrada.insert(0, f"{carga:g}")
        self._mensaje(
            f"Peso: {pct:g}% de {ref['rm']:g} kg = {exacto:.1f} kg "
            f"→ {carga:g} kg (discos de 2.5)"
        )

    # ------------------------------------------------------------------
    # Pestaña Progresión (ACSM 2009: principiantes / intermedios / avanzados)
    # ------------------------------------------------------------------
    def _crear_tab_progresion(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Progresión  ")

        # ----- ramas de árbol a la izquierda -----
        marco_nivel = ttk.LabelFrame(
            marco, text=" Nivel de entrenamiento ", padding=6,
            style="Gym.TLabelframe",
        )
        marco_nivel.pack(side="left", fill="y", padx=(8, 4), pady=8)

        arbol = ttk.Treeview(
            marco_nivel, show="tree", selectmode="browse", height=6,
            style="Gym.Treeview",
        )
        raiz = arbol.insert("", "end", iid="raiz", open=True,
                            text="🏋 Modelos de progresión")
        arbol.insert(raiz, "end", iid="principiantes",
                     text="🟢 Principiantes")
        arbol.insert(raiz, "end", iid="intermedios",
                     text="🟡 Intermedios")
        arbol.insert(raiz, "end", iid="avanzados", text="🔴 Avanzados")
        arbol.pack(fill="both", expand=True)

        tk.Label(
            marco_nivel, text="Basado en el Position Stand del ACSM "
            "(Med Sci Sports Exerc, 2009).", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO, wraplength=200, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        # ----- panel de contenido a la derecha -----
        marco_detalle = ttk.LabelFrame(
            marco, text=" Recomendaciones ", padding=6,
            style="Gym.TLabelframe",
        )
        marco_detalle.pack(side="left", fill="both", expand=True,
                           padx=(4, 8), pady=8)

        panel = tk.Text(
            marco_detalle, bg=GRIS_OSCURO, fg=BLANCO, relief="flat",
            font=("Segoe UI", 10), wrap="word", padx=14, pady=10,
            height=18,
        )
        panel.pack(side="left", fill="both", expand=True)
        barra_sc = ttk.Scrollbar(marco_detalle, command=panel.yview)
        barra_sc.pack(side="right", fill="y")
        panel.configure(yscrollcommand=barra_sc.set)
        panel.tag_configure("titulo", font=("Impact", 14), foreground=NEON)
        panel.tag_configure("seccion", font=("Segoe UI", 10, "bold"),
                            foreground=NARANJA)
        panel.tag_configure("normal", font=("Segoe UI", 10), foreground=BLANCO,
                            spacing3=4)
        panel.tag_configure("nota", font=("Segoe UI", 9),
                            foreground=GRIS_TEXTO)

        # ----- reglas generales + cita al pie -----
        pie = tk.Label(
            marco, text=REGLAS_GENERALES_PROGRESION
            + "\nAmerican College of Sports Medicine. Progression Models "
            "in Resistance Training for Healthy Adults. Med Sci Sports "
            "Exerc. 2009;41(3):687-708.",
            font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
            wraplength=760, justify="left",
        )
        pie.pack(fill="x", padx=8, pady=(0, 8))

        def mostrar_nivel(_evento=None):
            sel = arbol.selection()
            if not sel or sel[0] == "raiz":
                contenido = CONTENIDO_INTRO_PROGRESION
            else:
                contenido = CONTENIDO_PROGRESION.get(sel[0], "")
            panel.configure(state="normal")
            panel.delete("1.0", "end")
            panel.insert("1.0", contenido, "normal")
            # resalta los renglones que empiezan con ◆ como secciones
            linea = 1
            for renglon in contenido.split("\n"):
                if renglon.startswith("◆ "):
                    panel.delete(f"{linea}.0", f"{linea}.end")
                    panel.insert(f"{linea}.0", renglon[2:], "seccion")
                elif renglon.startswith("TITULO: "):
                    panel.delete(f"{linea}.0", f"{linea}.end")
                    panel.insert(f"{linea}.0", renglon[8:], "titulo")
                linea += 1
            panel.configure(state="disabled")

        arbol.bind("<<TreeviewSelect>>", mostrar_nivel)
        arbol.selection_set("principiantes")
        mostrar_nivel()

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
        ruta_json = os.path.join(base_dir(), nombre_json) if nombre_json else ""
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
            text=f"RUTINAS · {GRUPOS_ETIQUETAS.get(self.grupo, self.grupo).upper()}",
            font=("Impact", 15),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        self.marco_grupo = ttk.Frame(fila_titulo, style="Gym.TFrame")
        self.marco_grupo.pack(side="left", padx=(8, 10), pady=2)

        self.lbl_grupo_titulo = tk.Label(
            self.marco_grupo,
            text="Grupo:",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        )
        self.lbl_grupo_titulo.pack(side="left", padx=(0, 4))
        self.grupo_combo = ttk.Combobox(
            self.marco_grupo,
            values=[GRUPOS_ETIQUETAS.get(g["grupo"], g["grupo"].capitalize()) for g in self.grupos],
            state="readonly",
            width=12,
            style="Gym.TCombobox",
        )
        self.grupo_combo.pack(side="left")
        self.grupo_combo.set(self.grupo.capitalize())
        self.grupo_combo.bind("<<ComboboxSelected>>", self._al_cambiar_grupo)

        # Calculadora 1RM (por ejercicio, ramas de árbol) a la derecha
        tk.Button(
            fila_titulo,
            text="🏋 1RM",
            command=self._abrir_1rm,
            font=("Impact", 12),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        self.titulo.pack(side="left", fill="x", expand=True)

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
        self._crear_tab_progresion()
        self.notebook_rut.bind("<<NotebookTabChanged>>", self._al_cambiar_subpestana)
        self.cargar(getattr(self.app, "id_paciente_antro", None))

    def _crear_tab_calentamiento(self):
        marco = ttk.Frame(self.notebook_rut, style="Gym.TFrame")
        self.notebook_rut.add(marco, text="  Calentamiento  ")

        self.calent_items = self._cargar_catalogo_calentamiento()
        self.calent_paciente = {}
        self.calent_actual = None
        self.calent_foto = None

        self.lbl_calent = tk.Label(
            marco,
            text=f"Calentamiento dinámico · {len(self.calent_items)} fichas",
            font=("Segoe UI", 10),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        )
        self.lbl_calent.pack(anchor="w", padx=10, pady=(8, 4))

        contenedor = ttk.Frame(marco, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        izq = ttk.Frame(contenedor, style="Gym.TFrame")
        izq.pack(side="left", fill="both", padx=(0, 10))

        self.calent_tree = ttk.Treeview(
            izq, columns=("orden", "nombre", "dur"), show="headings",
            height=13, style="Gym.Treeview",
        )
        self.calent_tree.heading("orden", text="#")
        self.calent_tree.heading("nombre", text="Ejercicio")
        self.calent_tree.heading("dur", text="Duración")
        self.calent_tree.column("orden", width=36, anchor="center", stretch=False)
        self.calent_tree.column("nombre", width=268, anchor="w")
        self.calent_tree.column("dur", width=80, anchor="center", stretch=False)
        self.calent_tree.pack(fill="both", expand=True)
        self.calent_tree.bind("<<TreeviewSelect>>", self._al_seleccionar_calent)

        caja = ttk.LabelFrame(izq, text="Orden y duración", padding=6)
        caja.pack(fill="x", pady=(6, 0))

        tk.Label(
            caja, text="Orden:", font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
        ).grid(row=0, column=0, sticky="w")
        self.calent_orden_var = tk.StringVar()
        self.calent_orden = tk.Spinbox(
            caja, from_=1, to=40, width=4, textvariable=self.calent_orden_var,
            bg=GRIS, fg=BLANCO, insertbackground=BLANCO, relief="flat",
        )
        self.calent_orden.grid(row=0, column=1, padx=(4, 14))

        tk.Label(
            caja, text="Duración:", font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
        ).grid(row=0, column=2, sticky="w")
        self.calent_dur_var = tk.StringVar()
        self.calent_dur = ttk.Combobox(
            caja, textvariable=self.calent_dur_var, width=8, state="readonly",
            values=["30 s", "45 s", "60 s", "75 s", "90 s", "2 min", "3 min"],
            style="Gym.TCombobox",
        )
        self.calent_dur.grid(row=0, column=3, padx=(4, 14))

        ttk.Button(caja, text="GUARDAR", command=self._guardar_calent).grid(row=0, column=4)
        tk.Button(
            caja,
            text="IMPRIMIR",
            command=self._imprimir_calent,
            font=("Impact", 9),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=9,
            pady=3,
            cursor="hand2",
        ).grid(row=0, column=5, padx=(10, 0))

        der = ttk.Frame(contenedor, style="Gym.TFrame")
        der.pack(side="left", fill="both", expand=True)

        self.calent_img = tk.Label(
            der, text="Selecciona un ejercicio", bg=GRIS_OSCURO, fg=GRIS_TEXTO
        )
        self.calent_img.pack(fill="x")

        marco_desc = ttk.Frame(der, style="Gym.TFrame")
        marco_desc.pack(fill="both", expand=True, pady=(6, 0))
        self.calent_desc = tk.Text(
            marco_desc, height=10, wrap="word", bg=GRIS, fg=BLANCO, relief="flat",
            padx=8, pady=6, font=("Segoe UI", 9),
        )
        barra = ttk.Scrollbar(
            marco_desc, orient="vertical", command=self.calent_desc.yview
        )
        self.calent_desc.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.calent_desc.pack(side="left", fill="both", expand=True)
        self.calent_desc.configure(state="disabled")

        self._render_calentamiento()

    # ------------------------------------------------------------------
    # Calentamiento dinámico: catálogo, selección y orden del paciente
    # ------------------------------------------------------------------
    def _cargar_catalogo_calentamiento(self):
        ruta = os.path.join(base_dir(), "calentamiento_powerlifting.json")
        try:
            with open(ruta, encoding="utf-8") as fh:
                datos = json.load(fh)
        except Exception:
            return []
        return sorted(datos, key=lambda d: (int(d.get("orden", 0)), str(d.get("num", ""))))

    def _cargar_calentamiento_paciente(self):
        if not hasattr(self, "calent_tree"):
            return
        paciente_id = getattr(self, "paciente_id", None) or getattr(
            self.app, "id_paciente_antro", None
        )
        if paciente_id is None:
            self.calent_paciente = {}
        else:
            try:
                self.calent_paciente = database.get_calentamiento_paciente(paciente_id) or {}
            except Exception:
                self.calent_paciente = {}
        self._render_calentamiento()

    def _ficha_calentamiento(self, num):
        for ficha in getattr(self, "calent_items", []):
            if str(ficha.get("num")) == str(num):
                return ficha
        return None

    def _render_calentamiento(self):
        if not hasattr(self, "calent_tree"):
            return
        seleccion = self.calent_tree.selection()
        for item in self.calent_tree.get_children():
            self.calent_tree.delete(item)

        filas = []
        for ficha in getattr(self, "calent_items", []):
            num = str(ficha.get("num"))
            ajuste = (getattr(self, "calent_paciente", {}) or {}).get(num, {})
            orden = ajuste.get("orden", ficha.get("orden", 0))
            duracion = ajuste.get("duracion", ficha.get("duracion", ""))
            filas.append((int(orden), num, ficha.get("nombre", ""), duracion))
        filas.sort(key=lambda f: (f[0], f[1]))

        for orden, num, nombre, duracion in filas:
            self.calent_tree.insert("", "end", iid=num, values=(orden, nombre, duracion))

        if not seleccion:
            hijos = self.calent_tree.get_children()
            if hijos:
                self.calent_tree.selection_set(hijos[0])
                self.calent_tree.focus(hijos[0])
                self._al_seleccionar_calent()
            return

        for num in seleccion:
            if self.calent_tree.exists(num):
                self.calent_tree.selection_set(num)
                break

    def _al_seleccionar_calent(self, event=None):
        seleccion = self.calent_tree.selection()
        if not seleccion:
            return
        num = seleccion[0]
        ficha = self._ficha_calentamiento(num)
        if not ficha:
            return
        self.calent_actual = num

        ajuste = (getattr(self, "calent_paciente", {}) or {}).get(num, {})
        self.calent_orden_var.set(str(ajuste.get("orden", ficha.get("orden", ""))))
        self.calent_dur_var.set(str(ajuste.get("duracion", ficha.get("duracion", ""))))

        texto = f"{ficha.get('nombre', '')}\n\n{ficha.get('descripcion', '')}"
        self.calent_desc.configure(state="normal")
        self.calent_desc.delete("1.0", "end")
        self.calent_desc.insert("1.0", texto)
        self.calent_desc.configure(state="disabled")

        self._cargar_imagen_calent(ficha)

    def _cargar_imagen_calent(self, ficha):
        if ImageTk is None:
            self.calent_img.configure(image="", text="Sin vista previa (Pillow no disponible)")
            return
        ruta = os.path.join(
            RUTA_IMAGENES, "calentamiento", "cal_%s.jpeg" % ficha.get("imagen", "")
        )
        try:
            with Image.open(ruta) as imagen:
                copia = imagen.convert("RGB")
                copia.thumbnail((320, 250))
                self.calent_foto = ImageTk.PhotoImage(copia)
        except Exception:
            self.calent_foto = None
            self.calent_img.configure(image="", text="Sin ilustración")
            return
        self.calent_img.configure(image=self.calent_foto, text="")

    def _guardar_calent(self):
        num = getattr(self, "calent_actual", None)
        if not num:
            messagebox.showinfo("Calentamiento", "Selecciona un ejercicio de la lista.")
            return
        try:
            orden = int(str(self.calent_orden_var.get()).strip())
        except Exception:
            messagebox.showwarning("Calentamiento", "El orden debe ser un número entero.")
            return
        duracion = str(self.calent_dur_var.get()).strip()
        if not duracion:
            messagebox.showwarning("Calentamiento", "Elige una duración.")
            return

        self.calent_paciente[num] = {"orden": orden, "duracion": duracion}
        paciente_id = getattr(self, "paciente_id", None) or getattr(
            self.app, "id_paciente_antro", None
        )
        if paciente_id is not None:
            try:
                database.guardar_calentamiento_item(paciente_id, num, orden, duracion)
            except Exception as exc:
                messagebox.showerror("Calentamiento", "No se pudo guardar:\n%s" % exc)
                return
        self._render_calentamiento()
        self._mensaje("Calentamiento: orden %s, %s" % (orden, duracion))

    def _plan_calentamiento(self):
        """Fichas del calentamiento en el orden fijado para el paciente."""
        plan = []
        for ficha in getattr(self, "calent_items", []):
            num = str(ficha.get("num"))
            ajuste = (getattr(self, "calent_paciente", {}) or {}).get(num, {})
            plan.append(
                {
                    "num": num,
                    "nombre": ficha.get("nombre", ""),
                    "zona": ficha.get("zona", ""),
                    "equipo": ficha.get("equipo", ""),
                    "orden": int(ajuste.get("orden", ficha.get("orden", 0)) or 0),
                    "duracion": ajuste.get("duracion", ficha.get("duracion", "")),
                    "imagen": ficha.get("imagen", ""),
                    "descripcion": ficha.get("descripcion", ""),
                }
            )
        plan.sort(key=lambda f: (f["orden"], f["num"]))
        return plan

    def _imprimir_calent(self):
        """Genera el PDF del calentamiento y lo abre para impresión."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Calentamiento", "Selecciona un paciente antes de imprimir."
            )
            return
        plan = self._plan_calentamiento()
        if not plan:
            messagebox.showwarning(
                "Calentamiento", "No hay ejercicios de calentamiento para imprimir."
            )
            return

        paciente = database.obtener_paciente(paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{paciente_id}"
        ruta = calentamiento_print.ruta_temporal_pdf(nombre)
        try:
            calentamiento_print.generar_pdf_calentamiento(ruta, paciente, plan)
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            calentamiento_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
            )
            return

        self._mensaje("Calentamiento: reporte generado.")

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
                ("Descanso entre ejercicios (seg)", 10, ""),
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

        # --- Peso desde el 1RM: referencia y porcentaje ---
        fila_rm = ttk.Frame(campos, style="Gym.TFrame")
        fila_rm.grid(row=1, column=0, columnspan=5, sticky="w", padx=6, pady=(6, 0))
        tk.Label(
            fila_rm, text="1RM de referencia:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        self.combo_rm_ref = ttk.Combobox(
            fila_rm, width=34, state="readonly", style="Gym.TCombobox"
        )
        self.combo_rm_ref.pack(side="left", padx=(4, 12))
        self.combo_rm_ref.bind("<<ComboboxSelected>>", self._al_elegir_rm_ref)
        tk.Label(
            fila_rm, text="% del 1RM → peso:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        self.combo_rm_pct = ttk.Combobox(
            fila_rm, width=11, state="readonly", style="Gym.TCombobox"
        )
        self.combo_rm_pct.pack(side="left", padx=(4, 0))
        self.combo_rm_pct.bind("<<ComboboxSelected>>", self._al_elegir_pct_1rm)

        boton_alta = ttk.Frame(campos, style="Gym.TFrame")
        boton_alta.grid(row=0, column=5, rowspan=2, padx=(14, 4), sticky="s")
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
            ("desc_rep", "Desc. ej. (s)", 100, "center"),
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
        tk.Button(
            acciones,
            text="IMPRIMIR RUTINA",
            command=self._imprimir_rutina,
            font=("Impact", 9),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        ).pack(fill="x", pady=(6, 0))
        self.lbl_rutina_total = ttk.Label(
            acciones, text="0 ejercicios", style="Estado.TLabel"
        )
        self.lbl_rutina_total.pack(anchor="w", pady=(8, 0))

        # Primero reservan su espacio la tabla y el registro; el panel de
        # seleccion/previsualizacion se queda con el resto
        marco_rutina_pac.pack(side="bottom", fill="both", pady=(6, 0))
        marco_registro.pack(side="bottom", fill="x", pady=(6, 0))

        # --- Barra de días de la rutina semanal (patrón de Menús) ---
        barra_dias = ttk.Frame(contenedor_principal, style="Gym.TFrame")
        barra_dias.pack(side="bottom", fill="x", pady=(6, 0))
        tk.Label(
            barra_dias, text="Día:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left", padx=(6, 6))
        for dia in DIAS_SEMANA:
            btn = tk.Button(
                barra_dias, text=dia,
                command=lambda d=dia: self._cambiar_dia(d),
                font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
                activebackground=NARANJA, activeforeground=BLANCO,
                relief="flat", padx=8, pady=3, cursor="hand2",
            )
            btn.pack(side="left", padx=2)
            self.dia_buttons[dia] = btn
        self.btn_descanso = tk.Button(
            barra_dias, text="MARCAR DÍA DE DESCANSO",
            command=self._alternar_descanso,
            font=("Impact", 9), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=10, pady=3, cursor="hand2",
        )
        self.btn_descanso.pack(side="right", padx=(6, 0))

        superior.pack(fill="both", expand=True)

        self.marco_rutina_pac = marco_rutina_pac

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
        texto = self.grupo_combo.get().strip()
        elegido = {v: k for k, v in GRUPOS_ETIQUETAS.items()}.get(texto, texto.lower())
        if not elegido or elegido == self.grupo:
            return
        self._cargar_ejercicios(elegido)
        if self._subpestana_actual() != 2:
            self.titulo.configure(text=f"RUTINAS · {GRUPOS_ETIQUETAS.get(self.grupo, self.grupo).upper()}")
        self._poblar_combo_ejercicios()

    def _subpestana_actual(self):
        try:
            return self.notebook_rut.index("current")
        except Exception:
            return 1

    def _al_cambiar_subpestana(self, event=None):
        """En Estiramientos y Progresión el título y el filtro cambian."""
        sub = self._subpestana_actual()
        if sub == 2:
            self.titulo.configure(text="ESTIRAMIENTOS")
            self.marco_grupo.pack_forget()
            self._cargar_est_paciente()
        elif sub == 3:
            self.titulo.configure(text="PROGRESIÓN · MODELO ACSM 2009")
            self.marco_grupo.pack_forget()
        else:
            self.titulo.configure(text=f"RUTINAS · {GRUPOS_ETIQUETAS.get(self.grupo, self.grupo).upper()}")
            if not self.marco_grupo.winfo_ismapped():
                self.marco_grupo.pack(side="left", padx=(8, 10), pady=2, before=self.titulo)

    def _al_seleccionar_combo(self, event=None):
        idx = self.combo_ej.current()
        if idx < 0 or idx >= len(self.ejercicios):
            return
        ej = self.ejercicios[idx]
        self.ejercicio_seleccionado = ej
        self._mostrar_ejercicio(ej)
        # si hay un 1RM guardado de este ejercicio, se selecciona solo
        if getattr(self, "_rm_lista", None):
            etiqueta = self._buscar_ref_ejercicio()
            if etiqueta is not None and self.combo_rm_ref.get() != etiqueta:
                self.combo_rm_ref.set(etiqueta)
                self._llenar_pct_1rm()

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
        tk.Button(
            acciones,
            text="IMPRIMIR ESTIRAMIENTOS",
            command=self._imprimir_est,
            font=("Impact", 9),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        ).pack(fill="x", pady=(6, 0))
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
                        base_dir(),
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

    def _imprimir_est(self):
        """Genera el PDF de los estiramientos seleccionados (resumen +
        detalle con ilustración y descripción) y lo abre para impresión."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Estiramientos", "Selecciona un paciente antes de imprimir."
            )
            return
        seleccion = getattr(self, "est_seleccion", None)
        if not seleccion:
            messagebox.showwarning(
                "Estiramientos",
                "No hay estiramientos seleccionados para imprimir.",
            )
            return

        # la selección ya trae el catálogo unido (descripcion, imagen,
        # imagen_blob); se indexa por id para el detalle del reporte
        catalogo = {}
        for reg in seleccion:
            catalogo[reg.get("id_estiramiento")] = reg

        paciente = database.obtener_paciente(paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{paciente_id}"
        ruta = estiramientos_print.ruta_temporal_pdf(nombre)
        try:
            estiramientos_print.generar_pdf_estiramientos(
                ruta, paciente, seleccion, estiramientos_por_id=catalogo
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

        self._mensaje("Estiramientos: reporte generado.")

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

        # añadir a un día de descanso lo convierte en día de entrenamiento
        dia = getattr(self, "dia_actual", DIAS_SEMANA[0])
        filas_dia = [
            r for r in getattr(self, "rutina", [])
            if (r.get("dia") or "Lunes") == dia
        ]
        if any(r.get("descanso") for r in filas_dia) and not messagebox.askyesno(
            "Rutinas",
            f"{dia} está marcado como día de descanso.\n"
            f"¿Quitar el descanso y añadir el ejercicio?",
        ):
            return
        if any(r.get("descanso") for r in filas_dia):
            try:
                database.quitar_descanso(paciente_id, dia)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo quitar el descanso:\n{error}"
                )
                return

        datos = {
            "paciente_id": paciente_id,
            "dia": dia,
            "grupo": ej.get("grupo") or self.grupo,
            "num": ej.get("num"),
            "nombre": ej.get("nombre"),
            "equipo": ej.get("equipo"),
            "series": series,
            "repeticiones": repeticiones,
            "descanso_rep": self.reg_entradas["Descanso entre ejercicios (seg)"].get().strip(),
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
        if seleccion[0] == "descanso":
            # la fila "— DÍA DE DESCANSO —" también se quita aquí
            paciente_id = self._paciente_actual()
            try:
                database.quitar_descanso(
                    paciente_id, getattr(self, "dia_actual", DIAS_SEMANA[0])
                )
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo quitar el descanso:\n{error}"
                )
                return
            self._cargar_rutina()
            self._mensaje(f"{self.dia_actual}: día de descanso quitado.")
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
            "Rutinas",
            "¿Vaciar toda la rutina de este paciente (todos los días de la semana)?",
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

    def _imprimir_rutina(self):
        """Genera el PDF de la rutina (tabla resumen + detalle con
        imagen y descripción) y lo abre para impresión."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de imprimir."
            )
            return
        rutina = getattr(self, "rutina", None)
        if not rutina:
            messagebox.showwarning(
                "Rutinas", "No hay ejercicios en la rutina para imprimir."
            )
            return

        # el plan enriquece cada fila con la descripción y la ilustración
        # del catálogo para el detalle del reporte (las filas de descanso
        # no están en el catálogo)
        plan = []
        for fila in rutina:
            fila = dict(fila)
            if not fila.get("descanso"):
                try:
                    ficha = database.get_rutina_ejercicio(
                        fila.get("grupo"), fila.get("num")
                    )
                except Exception:
                    ficha = None
                if ficha:
                    for campo in ("descripcion", "imagen_blob", "imagen_nombre"):
                        fila[campo] = ficha.get(campo)
            plan.append(fila)

        paciente = database.obtener_paciente(paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{paciente_id}"
        ruta = rutina_print.ruta_temporal_pdf(nombre)
        try:
            rutina_print.generar_pdf_rutina(ruta, paciente, plan)
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            rutina_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
            )
            return

        self._mensaje("Rutina: reporte generado.")

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
        semana = getattr(self, "rutina", [])
        dia = getattr(self, "dia_actual", DIAS_SEMANA[0])
        filas = [r for r in semana if (r.get("dia") or "Lunes") == dia]
        descanso = any(r.get("descanso") for r in filas)
        self._resaltar_dia()
        if hasattr(self, "btn_descanso"):
            self.btn_descanso.configure(
                text="✓ QUITAR DESCANSO" if descanso else "MARCAR DÍA DE DESCANSO",
                bg=NARANJA if descanso else GRIS,
                fg=NEGRO if descanso else BLANCO,
            )
        if hasattr(self, "marco_rutina_pac"):
            self.marco_rutina_pac.configure(
                text=f"Rutina del paciente · {dia}"
                + (" · DESCANSO" if descanso else "")
            )
        if descanso:
            self.tree_rutina.insert(
                "", "end", iid="descanso",
                values=("—", "— DÍA DE DESCANSO —", "-", "-", "-", "-", "-", "-"),
            )
        else:
            posicion = 0
            for registro in filas:
                posicion += 1
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
        total_dia = len(filas) - (1 if descanso else 0)
        total_semana = len([r for r in semana if not r.get("descanso")])
        self.lbl_rutina_total.configure(
            text=f"{total_dia} ejercicio" + ("" if total_dia == 1 else "s")
            + f" · semana: {total_semana}"
        )

    # ------------------------------------------------------------------
    # Rutina semanal: día en edición y días de descanso
    # ------------------------------------------------------------------

    def _cambiar_dia(self, dia):
        if dia == self.dia_actual:
            return
        self.dia_actual = dia
        self._render_rutina()

    def _resaltar_dia(self):
        for dia, btn in getattr(self, "dia_buttons", {}).items():
            seleccionado = dia == self.dia_actual
            btn.configure(
                bg=NEON if seleccionado else GRIS,
                fg=NEGRO if seleccionado else BLANCO,
            )

    def _alternar_descanso(self):
        """Marca el día actual como descanso (borrando sus ejercicios,
        con confirmación) o quita la marca si ya era descanso."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de marcar descansos."
            )
            return
        dia = self.dia_actual
        filas = [
            r for r in getattr(self, "rutina", [])
            if (r.get("dia") or "Lunes") == dia
        ]
        if any(r.get("descanso") for r in filas):
            try:
                database.quitar_descanso(paciente_id, dia)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo quitar el descanso:\n{error}"
                )
                return
            self._cargar_rutina()
            self._mensaje(f"{dia}: día de descanso quitado.")
            return
        ejercicios = [r for r in filas if not r.get("descanso")]
        if ejercicios and not messagebox.askyesno(
            "Rutinas",
            f"{dia} tiene {len(ejercicios)} ejercicio(s).\n"
            f"¿Borrarlos y marcar el día como descanso?",
        ):
            return
        try:
            database.marcar_descanso(paciente_id, dia)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo marcar el descanso:\n{error}"
            )
            return
        self._cargar_rutina()
        self._mensaje(f"{dia}: marcado como día de descanso.")

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
        self._cargar_calentamiento_paciente()
        self._recargar_referencias_1rm()

    def refrescar_estado(self):
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id != self.paciente_id:
            self.cargar(paciente_id)
            return
        # Mismo paciente: refresca la selección de estiramientos por si cambió
        # desde la pestaña Estiramientos.
        self._cargar_est_paciente()
