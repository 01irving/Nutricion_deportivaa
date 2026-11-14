import io
import json
import os
import unicodedata
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

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

# ----------------------------------------------------------------------
# Plantillas de rutina semanal (patrón del combo "Menú:" de la pestaña
# Menús). Los ejercicios son (grupo, num, marca) del catálogo de
# rutinas_ejercicios; marca "superserie" agrupa pares que se realizan
# sin descanso entre sí. None en la semana = día de descanso.
# ----------------------------------------------------------------------
PLANTILLAS_SEMANA = (
    {
        # Pedersen et al. 2022, BMC Sports Science, Medicine and
        # Rehabilitation 14:87 — Tabla 1, grupo SPLIT: 4 sesiones
        # (2 superiores + 2 inferiores), 3 series de 8-12 RM con
        # ~1 min de descanso entre series.
        "nombre": "Split 4 días · Tren superior / inferior (Pedersen 2022)",
        "series": "3",
        "repeticiones": "8-12",
        "descanso_series": "60",
        "sesiones": {
            "Tren superior": (
                ("espalda", "03", ""),        # Lat pulldown
                ("pectorales", "02", ""),     # Bench press
                ("espalda", "06", ""),        # Cable seated row
                ("brazos", "13", "superserie"),   # Triceps press en cable
                ("brazos", "05", "superserie"),   # Biceps curl en cable
            ),
            "Tren inferior": (
                ("piernas", "06", ""),        # Leg press
                ("espalda", "14", ""),        # Stiff-legged deadlift
                ("piernas", "09", ""),        # Leg extension
                ("gluteos", "06", ""),        # Hip thrust
            ),
        },
        "semana": {
            "Lunes": "Tren superior",
            "Martes": "Tren inferior",
            "Miércoles": None,
            "Jueves": "Tren superior",
            "Viernes": "Tren inferior",
            "Sábado": None,
            "Domingo": None,
        },
    },
)
PLACEHOLDER_PLANTILLA = "— Elegir y abrir —"


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
    # Rutinas semanales predefinidas (plantilla → cuadro → aplicar)
    # ------------------------------------------------------------------

    def _al_elegir_plantilla(self, event=None):
        """Abrir el cuadro de la plantilla semanal elegida: una de las
        fijas del estudio o una rutina semanal guardada con nombre
        (marcada con estrella); al cerrarlo el combo vuelve al texto de
        invitación."""
        elegida = self.combo_plantilla.get()
        if elegida.startswith("★ "):
            guardada = next(
                (r for r in self._semanales_guardadas()
                 if r["nombre"] == elegida[2:]),
                None,
            )
            if guardada is not None:
                self._abrir_plantilla_semana(self._plantilla_de_guardada(guardada))
        else:
            idx = self.combo_plantilla.current()
            if not 0 <= idx < len(PLANTILLAS_SEMANA):
                return
            self._abrir_plantilla_semana(PLANTILLAS_SEMANA[idx])
        self.combo_plantilla.set(PLACEHOLDER_PLANTILLA)

    def _semanales_guardadas(self):
        """Rutinas semanales guardadas por el usuario (lista vacía si la
        tabla aún no existe por una BD muy vieja)."""
        try:
            return database.get_rutinas_guardadas(semanal=1)
        except Exception:
            return []

    def _refrescar_combo_plantilla(self):
        """Combo Rutina semanal: las plantillas fijas del estudio más las
        rutinas semanales guardadas con nombre (prefijo estrella)."""
        if not hasattr(self, "combo_plantilla"):
            return
        valores = [p["nombre"] for p in PLANTILLAS_SEMANA] + [
            "★ " + r["nombre"] for r in self._semanales_guardadas()
        ]
        self.combo_plantilla.configure(values=valores)
        self.combo_plantilla.set(PLACEHOLDER_PLANTILLA)

    def _plantilla_de_guardada(self, guardada):
        """Convierte una rutina semanal guardada en la estructura que
        consumen el cuadro y la aplicación de plantillas: semana (dia ->
        sesión o None) y sesiones (nombre -> fichas con su propia
        prescripción). La sesión es la nota guardada con cada ejercicio;
        si un día no tiene nota, el propio nombre del día hace de sesión."""
        rutina = database.get_rutina_guardada(guardada["id_rutina_guardada"])
        semana = {dia: None for dia in DIAS_SEMANA}
        sesiones = {}
        for e in rutina["ejercicios"]:
            if e.get("descanso"):
                continue
            sesion = (e.get("notas") or "").strip() or (e.get("dia") or "")
            semana[e["dia"]] = sesion
            sesiones.setdefault(sesion, []).append(dict(e))
        return {
            "nombre": rutina["nombre"],
            "guardada": True,
            "semana": semana,
            "sesiones": {s: tuple(fs) for s, fs in sesiones.items()},
            "series": "",
            "repeticiones": "",
            "descanso_series": "",
        }

    def _fichas_plantilla(self, plantilla):
        """Fichas del catálogo por sesión de la plantilla (copia editable
        para el cuadro) y lista de entradas sin ficha en el catálogo."""
        sesiones = {}
        faltan = []
        for sesion, ejercicios in plantilla["sesiones"].items():
            filas = []
            for grupo, num, marca in ejercicios:
                try:
                    ficha = database.get_rutina_ejercicio(grupo, num)
                except Exception:
                    ficha = None
                if ficha is None:
                    faltan.append(f"{grupo} #{num}")
                    ficha = {"nombre": f"{grupo} #{num}", "equipo": ""}
                ficha = dict(ficha)
                ficha["marca"] = marca
                filas.append(ficha)
            sesiones[sesion] = filas
        return sesiones, faltan

    def _abrir_plantilla_semana(self, plantilla):
        """Cuadro de la rutina semanal: vista previa de la semana y de cada
        sesión (con posibilidad de quitar ejercicios) y botón para aplicar
        la semana completa a la rutina del paciente."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas",
                "Selecciona un paciente antes de cargar una rutina semanal.",
            )
            return

        if plantilla.get("guardada"):
            # rutina semanal guardada: las fichas ya traen nombre, equipo
            # y prescripción; no hace falta resolverlas en el catálogo
            sesiones = {
                s: [dict(f) for f in fs]
                for s, fs in plantilla["sesiones"].items()
            }
            faltan = []
        else:
            sesiones, faltan = self._fichas_plantilla(plantilla)

        dialogo = tk.Toplevel(self.marco)
        dialogo.title(f"Rutina semanal · {plantilla['nombre']}")
        dialogo.configure(bg=GRIS_OSCURO)
        dialogo.transient(self.marco)
        dialogo.grab_set()

        tk.Label(
            dialogo,
            text=plantilla["nombre"].upper(),
            font=("Impact", 13),
            fg=NEON,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        # --- vista previa de la semana ---
        tk.Label(
            dialogo, text="Semana:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12)
        marco_semana = tk.Frame(dialogo, bg=GRIS_OSCURO)
        marco_semana.pack(fill="x", padx=12)
        cols_semana = ("dia", "sesion", "total")
        tree_semana = ttk.Treeview(
            marco_semana, columns=cols_semana, show="headings", height=7,
            style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("dia", "Día", 90, "w"),
            ("sesion", "Sesión", 150, "w"),
            ("total", "Ejercicios", 90, "center"),
        ):
            tree_semana.heading(col, text=texto, anchor=alineacion)
            tree_semana.column(col, width=ancho, minwidth=ancho, anchor=alineacion)
        tree_semana.pack(side="left", fill="x", expand=True)
        barra_semana = ttk.Scrollbar(
            marco_semana, orient="vertical", command=tree_semana.yview
        )
        tree_semana.configure(yscrollcommand=barra_semana.set)
        barra_semana.pack(side="right", fill="y")

        # --- selector de sesión con sus ejercicios abajo ---
        fila_sesion = tk.Frame(dialogo, bg=GRIS_OSCURO)
        fila_sesion.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(
            fila_sesion, text="Sesión:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        nombres_sesiones = list(sesiones)
        combo_sesion = ttk.Combobox(
            fila_sesion, values=nombres_sesiones, state="readonly",
            style="Gym.TCombobox", width=18,
        )
        combo_sesion.current(0)
        combo_sesion.pack(side="left", padx=(4, 12))

        marco_sesion = tk.Frame(dialogo, bg=GRIS_OSCURO)
        marco_sesion.pack(fill="both", expand=True, padx=12, pady=(4, 0))
        cols_sesion = ("num", "nombre", "equipo", "presc")
        tree_sesion = ttk.Treeview(
            marco_sesion, columns=cols_sesion, show="headings", height=6,
            style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("num", "#", 30, "center"),
            ("nombre", "Ejercicio", 300, "w"),
            ("equipo", "Equipo", 130, "w"),
            ("presc", "Series × Reps", 100, "center"),
        ):
            tree_sesion.heading(col, text=texto, anchor=alineacion)
            tree_sesion.column(col, width=ancho, minwidth=ancho, anchor=alineacion)
        tree_sesion.pack(side="left", fill="both", expand=True)
        barra_sesion = ttk.Scrollbar(
            marco_sesion, orient="vertical", command=tree_sesion.yview
        )
        tree_sesion.configure(yscrollcommand=barra_sesion.set)
        barra_sesion.pack(side="right", fill="y")

        def pintar_semana():
            for item in tree_semana.get_children():
                tree_semana.delete(item)
            for dia in DIAS_SEMANA:
                sesion = plantilla["semana"].get(dia)
                if sesion is None:
                    tree_semana.insert("", "end", values=(dia, "DESCANSO", "—"))
                else:
                    total = len(sesiones.get(sesion, []))
                    tree_semana.insert(
                        "", "end", values=(dia, sesion, total)
                    )

        def pintar_sesion(*_):
            sesion = combo_sesion.get()
            for item in tree_sesion.get_children():
                tree_sesion.delete(item)
            for posicion, ficha in enumerate(sesiones.get(sesion, []), start=1):
                nombre = ficha.get("nombre") or ""
                if ficha.get("marca") == "superserie":
                    nombre += "  (superserie)"
                # en las guardadas la prescripción va ejercicio a ejercicio
                series = ficha.get("series") or plantilla.get("series") or "—"
                reps = (
                    ficha.get("repeticiones")
                    or plantilla.get("repeticiones") or "—"
                )
                tree_sesion.insert(
                    "", "end", iid=str(posicion - 1),
                    values=(
                        posicion,
                        nombre,
                        ficha.get("equipo") or "-",
                        f"{series} × {reps}",
                    ),
                )

        def quitar_de_sesion():
            seleccion = tree_sesion.selection()
            if not seleccion:
                return
            indice = int(seleccion[0])
            sesion = combo_sesion.get()
            if 0 <= indice < len(sesiones.get(sesion, [])):
                sesiones[sesion].pop(indice)
                pintar_sesion()
                pintar_semana()

        tk.Button(
            fila_sesion,
            text="Quitar seleccionado",
            command=quitar_de_sesion,
            font=("Segoe UI", 8, "bold"),
            fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left")

        combo_sesion.bind("<<ComboboxSelected>>", pintar_sesion)
        pintar_semana()
        pintar_sesion()

        if plantilla.get("guardada"):
            nota = "Prescripción guardada por ejercicio (columna Series × Reps)."
        else:
            nota = (
                f"{plantilla['series']} series × {plantilla['repeticiones']} "
                f"repeticiones · descanso entre series ≈{plantilla['descanso_series']} s"
            )
        tk.Label(
            dialogo, text=nota, font=("Segoe UI", 8, "italic"),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO, justify="left",
        ).pack(anchor="w", padx=12, pady=(6, 0))
        if faltan:
            tk.Label(
                dialogo,
                text="No está en el catálogo: " + ", ".join(dict.fromkeys(faltan)),
                font=("Segoe UI", 8),
                fg=NARANJA, bg=GRIS_OSCURO, justify="left",
            ).pack(anchor="w", padx=12)

        def aplicar():
            self._aplicar_plantilla_semana(plantilla, sesiones, dialogo)

        tk.Button(
            dialogo,
            text="APLICAR A LA SEMANA",
            command=aplicar,
            font=("Impact", 10),
            fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(pady=(8, 12))

        dialogo.wait_window()

    def _aplicar_plantilla_semana(self, plantilla, sesiones, dialogo):
        """Reemplaza la rutina semanal del paciente por la plantilla: las
        sesiones de la semana con su nota ("Tren superior"/"Tren inferior")
        y los días de descanso marcados."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de aplicar la plantilla."
            )
            return
        total_actual = len(
            [r for r in getattr(self, "rutina", []) if not r.get("descanso")]
        )
        if total_actual:
            paciente = database.obtener_paciente(paciente_id) or {}
            nombre = paciente.get("nombre") or f"paciente {paciente_id}"
            if not messagebox.askyesno(
                "Rutinas",
                f"¿Reemplazar la rutina semanal de {nombre} "
                f"({total_actual} ejercicio{'s' if total_actual != 1 else ''}) "
                f"por «{plantilla['nombre']}»?",
            ):
                return
        try:
            database.delete_rutinas_paciente(paciente_id)
            for dia, sesion in plantilla["semana"].items():
                if sesion is None:
                    database.marcar_descanso(paciente_id, dia)
                    continue
                for ficha in sesiones.get(sesion, []):
                    database.insert_rutina_paciente(
                        {
                            "paciente_id": paciente_id,
                            "dia": dia,
                            "grupo": ficha.get("grupo"),
                            "num": ficha.get("num"),
                            "nombre": ficha.get("nombre"),
                            "equipo": ficha.get("equipo"),
                            # las guardadas traen prescripción propia; las
                            # fijas la toman de la plantilla
                            "series": ficha.get("series") or plantilla["series"],
                            "repeticiones": (
                                ficha.get("repeticiones")
                                or plantilla["repeticiones"]
                            ),
                            "descanso_rep": ficha.get("descanso_rep") or "",
                            "descanso_series": (
                                ficha.get("descanso_series")
                                or plantilla["descanso_series"]
                            ),
                            "peso": ficha.get("peso") or "",
                            "notas": sesion,
                        }
                    )
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo aplicar la plantilla:\n{error}"
            )
            return

        # deja seleccionado el primer día de entrenamiento (tren superior)
        entrenamiento = next(
            (d for d in DIAS_SEMANA if plantilla["semana"].get(d)), DIAS_SEMANA[0]
        )
        self.dia_actual = entrenamiento
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(f"Rutina semanal aplicada: {plantilla['nombre']}")
        dialogo.destroy()

    # ------------------------------------------------------------------
    # Rutinas guardadas con nombre (biblioteca del entrenador, común a
    # todos los pacientes): simples (lista de ejercicios con su
    # prescripción) y semanales (la semana completa del paciente con
    # sesiones y descansos). Patrón de "Menús guardados" en Menús.
    # ------------------------------------------------------------------

    def _guardar_semana_actual(self):
        """Guarda la rutina semanal cargada del paciente como rutina con
        nombre (upsert): sesiones, días de descanso y la prescripción de
        cada ejercicio quedan en la biblioteca y aparecen en el combo
        Rutina semanal marcados con estrella."""
        rutina = getattr(self, "rutina", [])
        con_ejercicios = [r for r in rutina if not r.get("descanso")]
        if not con_ejercicios:
            messagebox.showwarning(
                "Rutinas",
                "La rutina está vacía: añade ejercicios antes de guardar la semana.",
            )
            return
        nombre = simpledialog.askstring(
            "Rutinas",
            "Nombre de la rutina semanal:",
            parent=self.marco.winfo_toplevel(),
        )
        nombre = (nombre or "").strip()
        if not nombre:
            return
        if any(r["nombre"] == nombre for r in database.get_rutinas_guardadas()):
            if not messagebox.askyesno(
                "Rutinas", f"«{nombre}» ya existe. ¿Sobrescribirla?"
            ):
                return
        filas = []
        for r in rutina:
            filas.append(
                {
                    "dia": r.get("dia"),
                    "orden": r.get("orden"),
                    "descanso": 1 if r.get("descanso") else 0,
                    "grupo": r.get("grupo"),
                    "num": r.get("num"),
                    "nombre": r.get("nombre"),
                    "equipo": r.get("equipo"),
                    "series": r.get("series"),
                    "repeticiones": r.get("repeticiones"),
                    "descanso_rep": r.get("descanso_rep"),
                    "descanso_series": r.get("descanso_series"),
                    "peso": r.get("peso"),
                    "notas": r.get("notas"),
                }
            )
        try:
            database.guardar_rutina_guardada(nombre, True, filas)
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo guardar la semana:\n{error}"
            )
            return
        self._refrescar_combo_plantilla()
        self._pintar_rutinas_guardadas()
        self._mensaje(
            f"Rutina semanal guardada: «{nombre}» "
            f"({len(con_ejercicios)} ejercicios)."
        )

    def _crear_seccion_rutinas_guardadas(self, marco):
        """Tabla de la biblioteca de rutinas guardadas incrustada en la
        sub-pestaña, debajo de la rutina del paciente: lista las simples
        y las semanales con sus botones (antes abría una ventana)."""
        marco_lista = tk.Frame(marco, bg=GRIS_OSCURO)
        marco_lista.pack(fill="both", expand=True)
        columnas = ("nombre", "tipo", "detalle", "creado_en")
        self.tree_guardadas = ttk.Treeview(
            marco_lista, columns=columnas, show="headings", height=4,
            style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("nombre", "Nombre", 280, "w"),
            ("tipo", "Tipo", 80, "center"),
            ("detalle", "Contenido", 220, "w"),
            ("creado_en", "Creada", 130, "center"),
        ):
            self.tree_guardadas.heading(col, text=texto, anchor=alineacion)
            self.tree_guardadas.column(
                col, width=ancho, minwidth=ancho, anchor=alineacion
            )
        self.tree_guardadas.pack(side="left", fill="both", expand=True)
        barra = ttk.Scrollbar(
            marco_lista, orient="vertical", command=self.tree_guardadas.yview
        )
        self.tree_guardadas.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        # doble clic: editar una simple / abrir una semanal
        self.tree_guardadas.bind(
            "<Double-1>", lambda _e: self._editar_rutina_guardada()
        )

        fila_botones = tk.Frame(marco, bg=GRIS_OSCURO)
        fila_botones.pack(fill="x", pady=(6, 0))
        for texto, comando, estilo in (
            ("NUEVA RUTINA", self._nueva_rutina_guardada, "principal"),
            ("EDITAR", self._editar_rutina_guardada, "secundario"),
            ("APLICAR AL DÍA", self._aplicar_rutina_guardada, "principal"),
            ("ABRIR SEMANAL", self._abrir_rutina_guardada_semanal, "principal"),
            ("ELIMINAR", self._eliminar_rutina_guardada, "peligro"),
        ):
            tk.Button(
                fila_botones,
                text=texto,
                command=comando,
                font=("Segoe UI", 8, "bold"),
                fg={"principal": NEGRO, "secundario": BLANCO,
                    "peligro": NEON}[estilo],
                bg={"principal": NEON, "secundario": GRIS,
                    "peligro": GRIS}[estilo],
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=10,
                pady=3,
                cursor="hand2",
            ).pack(side="left", padx=(0, 6))
        self._pintar_rutinas_guardadas()

    def _pintar_rutinas_guardadas(self):
        """Rellena la tabla de rutinas guardadas con la biblioteca."""
        if not hasattr(self, "tree_guardadas"):
            return
        self.tree_guardadas.delete(*self.tree_guardadas.get_children())
        try:
            guardadas = database.get_rutinas_guardadas()
        except Exception:
            guardadas = []
        for r in guardadas:
            if r["semanal"]:
                tipo = "Semanal"
                detalle = (
                    f"{r['dias']} día" + ("" if r["dias"] == 1 else "s")
                    + f" con {r['ejercicios']} ejercicio"
                    + ("" if r["ejercicios"] == 1 else "s")
                )
            else:
                tipo = "Rutina"
                detalle = (
                    f"{r['ejercicios']} ejercicio"
                    + ("" if r["ejercicios"] == 1 else "s")
                )
            self.tree_guardadas.insert(
                "", "end", iid=str(r["id_rutina_guardada"]),
                values=(
                    r["nombre"], tipo, detalle, r.get("creado_en") or "",
                ),
            )

    def _rutina_guardada_seleccionada(self):
        """Devuelve la rutina guardada elegida en la tabla (o None)."""
        seleccion = self.tree_guardadas.selection()
        if not seleccion:
            messagebox.showinfo(
                "Rutinas", "Selecciona una rutina guardada de la lista."
            )
            return None
        return database.get_rutina_guardada(int(seleccion[0]))

    def _nueva_rutina_guardada(self):
        """Abre el cuadro para armar una rutina nueva y refresca la tabla."""
        self._abrir_crear_rutina()
        self._pintar_rutinas_guardadas()

    def _editar_rutina_guardada(self):
        """Edita la rutina simple elegida; las semanales se ajustan
        guardando de nuevo la semana del paciente con el mismo nombre."""
        guardada = self._rutina_guardada_seleccionada()
        if guardada is None:
            return
        if guardada["semanal"]:
            messagebox.showinfo(
                "Rutinas",
                "Las rutinas semanales se ajustan guardando de nuevo la "
                "semana del paciente con el mismo nombre.",
            )
            return
        self._abrir_crear_rutina(existente=guardada)
        self._pintar_rutinas_guardadas()

    def _aplicar_rutina_guardada(self):
        """Aplica la rutina simple elegida al día activo del paciente."""
        guardada = self._rutina_guardada_seleccionada()
        if guardada is None:
            return
        if guardada["semanal"]:
            messagebox.showinfo(
                "Rutinas",
                "«" + guardada["nombre"] + "» es semanal: usa Abrir semanal.",
            )
            return
        self._aplicar_rutina_guardada_al_dia(guardada)

    def _abrir_rutina_guardada_semanal(self):
        """Abre la rutina semanal elegida en el cuadro de plantillas
        (previsualización y aplicación a la semana del paciente)."""
        guardada = self._rutina_guardada_seleccionada()
        if guardada is None:
            return
        if not guardada["semanal"]:
            messagebox.showinfo(
                "Rutinas",
                "«" + guardada["nombre"] + "» es una rutina simple: "
                "usa Aplicar al día.",
            )
            return
        self._abrir_plantilla_semana(self._plantilla_de_guardada(guardada))

    def _eliminar_rutina_guardada(self):
        """Elimina de la biblioteca la rutina elegida (los pacientes no
        se tocan)."""
        guardada = self._rutina_guardada_seleccionada()
        if guardada is None:
            return
        if not messagebox.askyesno(
            "Rutinas",
            f"¿Eliminar «{guardada['nombre']}»? "
            "(no toca la rutina de los pacientes)",
        ):
            return
        database.delete_rutina_guardada(guardada["id_rutina_guardada"])
        self._pintar_rutinas_guardadas()
        self._refrescar_combo_plantilla()
        self._mensaje(f"Rutina eliminada: «{guardada['nombre']}».")

    def _aplicar_rutina_guardada_al_dia(self, guardada):
        """Añade al día activo del paciente los ejercicios de una rutina
        simple guardada, con su prescripción; si el día está marcado como
        descanso ofrece quitar la marca (patrón de Añadir ejercicio)."""
        paciente_id = self._paciente_actual()
        if paciente_id is None:
            messagebox.showwarning(
                "Rutinas", "Selecciona un paciente antes de aplicar la rutina."
            )
            return
        ejercicios = [
            e for e in guardada["ejercicios"] if not e.get("descanso")
        ]
        if not ejercicios:
            messagebox.showwarning(
                "Rutinas", "La rutina guardada no tiene ejercicios."
            )
            return
        dia = getattr(self, "dia_actual", DIAS_SEMANA[0])
        filas = [
            r for r in getattr(self, "rutina", [])
            if (r.get("dia") or "Lunes") == dia
        ]
        if any(r.get("descanso") for r in filas):
            if not messagebox.askyesno(
                "Rutinas",
                f"{dia} está marcado como día de descanso.\n"
                "¿Quitar el descanso y añadir los ejercicios?",
            ):
                return
            database.quitar_descanso(paciente_id, dia)
        paciente = database.obtener_paciente(paciente_id) or {}
        nombre_paciente = paciente.get("nombre") or f"paciente {paciente_id}"
        if not messagebox.askyesno(
            "Rutinas",
            f"¿Añadir {len(ejercicios)} ejercicio"
            + ("" if len(ejercicios) == 1 else "s")
            + f" de «{guardada['nombre']}» al {dia} de {nombre_paciente}?",
        ):
            return
        try:
            for ficha in ejercicios:
                database.insert_rutina_paciente(
                    {
                        "paciente_id": paciente_id,
                        "dia": dia,
                        "grupo": ficha.get("grupo"),
                        "num": ficha.get("num"),
                        "nombre": ficha.get("nombre"),
                        "equipo": ficha.get("equipo"),
                        "series": ficha.get("series"),
                        "repeticiones": ficha.get("repeticiones"),
                        "descanso_rep": ficha.get("descanso_rep"),
                        "descanso_series": ficha.get("descanso_series"),
                        "peso": ficha.get("peso"),
                    }
                )
        except Exception as error:
            messagebox.showerror(
                "Rutinas", f"No se pudo aplicar la rutina:\n{error}"
            )
            return
        self._cargar_rutina()
        self._marcar_rutina_guardada()
        self._mensaje(f"Aplicada «{guardada['nombre']}» al {dia}.")

    def _abrir_crear_rutina(self, existente=None):
        """Cuadro para crear (o editar) una rutina simple con nombre: se
        eligen ejercicios del catálogo (grupo + ejercicio) con su
        prescripción y se agregan a la lista; GUARDAR RUTINA la escribe en
        la biblioteca (upsert por nombre) sin tocar a los pacientes."""
        dialogo = tk.Toplevel(self.marco)
        titulo = "Editar rutina" if existente else "Nueva rutina"
        dialogo.title(titulo)
        dialogo.configure(bg=GRIS_OSCURO)
        dialogo.transient(self.marco)
        dialogo.grab_set()

        tk.Label(
            dialogo,
            text=titulo.upper(),
            font=("Impact", 13),
            fg=NEON,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12, pady=(10, 2))

        tk.Label(
            dialogo, text="Nombre:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12)
        entrada_nombre = ttk.Entry(dialogo, width=38, style="Gym.TEntry")
        entrada_nombre.pack(anchor="w", padx=12, pady=(0, 8))

        # selector de ejercicio del catálogo (grupo -> ejercicios)
        fila_sel = tk.Frame(dialogo, bg=GRIS_OSCURO)
        fila_sel.pack(fill="x", padx=12)
        tk.Label(
            fila_sel, text="Grupo:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        combo_grupo = ttk.Combobox(
            fila_sel, state="readonly", width=13, style="Gym.TCombobox",
        )
        grupos = [g["grupo"] for g in database.get_rutinas_grupos()]
        combo_grupo.configure(values=grupos)
        combo_grupo.pack(side="left", padx=(4, 10))

        tk.Label(
            fila_sel, text="Ejercicio:", font=("Segoe UI", 8),
            fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        ).pack(side="left")
        combo_ej = ttk.Combobox(
            fila_sel, state="readonly", width=30, style="Gym.TCombobox",
        )
        combo_ej.pack(side="left", fill="x", expand=True, padx=(4, 0))

        fichas_grupo = []

        def poblar_ejercicios(*_):
            fichas_grupo.clear()
            try:
                fichas_grupo.extend(
                    database.get_rutinas_ejercicios(combo_grupo.get())
                )
            except Exception:
                pass
            combo_ej.configure(
                values=[
                    f"{f['num']}. {f['nombre']} ({f['equipo'] or 'sin equipo'})"
                    for f in fichas_grupo
                ]
            )
            if fichas_grupo:
                combo_ej.current(0)
            else:
                combo_ej.set("")

        combo_grupo.bind("<<ComboboxSelected>>", poblar_ejercicios)
        if grupos:
            combo_grupo.current(0)
        poblar_ejercicios()

        # prescripción por defecto del ejercicio agregado (misma que el
        # formulario de la rutina del paciente)
        marco_presc = tk.Frame(dialogo, bg=GRIS_OSCURO)
        marco_presc.pack(fill="x", padx=12, pady=(8, 0))
        entradas = {}
        for col, texto, clave, defecto in (
            (0, "Series", "series", "3"),
            (1, "Repeticiones", "repeticiones", "12"),
            (2, "Descanso ej. (s)", "descanso_rep", ""),
            (3, "Descanso serie (s)", "descanso_series", ""),
            (4, "Peso (kg)", "peso", ""),
        ):
            tk.Label(
                marco_presc, text=texto, font=("Segoe UI", 8),
                fg=GRIS_TEXTO, bg=GRIS_OSCURO,
            ).grid(row=0, column=col, sticky="w", padx=(0, 6))
            entrada = ttk.Entry(marco_presc, width=9, style="Gym.TEntry")
            entrada.grid(row=1, column=col, sticky="w", padx=(0, 6))
            if defecto:
                entrada.insert(0, defecto)
            entradas[clave] = entrada

        ejercicios = []
        if existente:
            entrada_nombre.insert(0, existente["nombre"])
            ejercicios.extend(
                [dict(e) for e in existente["ejercicios"] if not e.get("descanso")]
            )

        columnas = ("nombre", "equipo", "series", "reps", "desc_rep", "desc_serie", "peso")
        tree = ttk.Treeview(
            dialogo, columns=columnas, show="headings", height=8,
            style="Gym.Treeview",
        )
        for col, texto, ancho, alineacion in (
            ("nombre", "Ejercicio", 240, "w"),
            ("equipo", "Equipo", 110, "w"),
            ("series", "Series", 50, "center"),
            ("reps", "Reps", 60, "center"),
            ("desc_rep", "Desc. ej.", 60, "center"),
            ("desc_serie", "Desc. serie", 70, "center"),
            ("peso", "Peso", 60, "center"),
        ):
            tree.heading(col, text=texto, anchor=alineacion)
            tree.column(col, width=ancho, minwidth=ancho, anchor=alineacion)

        def pintar_lista():
            tree.delete(*tree.get_children())
            for posicion, ficha in enumerate(ejercicios):
                tree.insert(
                    "", "end", iid=str(posicion),
                    values=(
                        ficha["nombre"],
                        ficha.get("equipo") or "-",
                        ficha.get("series") or "-",
                        ficha.get("repeticiones") or "-",
                        ficha.get("descanso_rep") or "-",
                        ficha.get("descanso_series") or "-",
                        ficha.get("peso") or "-",
                    ),
                )

        def agregar():
            indice = combo_ej.current()
            if not 0 <= indice < len(fichas_grupo):
                messagebox.showwarning(
                    "Rutinas", "Elige un ejercicio del catálogo.", parent=dialogo
                )
                return
            ficha = fichas_grupo[indice]
            ejercicios.append(
                {
                    "grupo": ficha.get("grupo"),
                    "num": ficha.get("num"),
                    "nombre": ficha.get("nombre"),
                    "equipo": ficha.get("equipo"),
                    "series": entradas["series"].get().strip(),
                    "repeticiones": entradas["repeticiones"].get().strip(),
                    "descanso_rep": entradas["descanso_rep"].get().strip(),
                    "descanso_series": entradas["descanso_series"].get().strip(),
                    "peso": entradas["peso"].get().strip(),
                }
            )
            pintar_lista()
            entradas["peso"].delete(0, "end")

        def quitar():
            seleccion = tree.selection()
            if not seleccion:
                return
            indice = int(seleccion[0])
            if 0 <= indice < len(ejercicios):
                ejercicios.pop(indice)
                pintar_lista()

        def guardar():
            nombre = entrada_nombre.get().strip()
            if not nombre:
                messagebox.showwarning(
                    "Rutinas", "Ponle un nombre a la rutina.", parent=dialogo
                )
                return
            if not ejercicios:
                messagebox.showwarning(
                    "Rutinas", "Añade al menos un ejercicio.", parent=dialogo
                )
                return
            nombre_repetido = nombre != (existente or {}).get("nombre") and any(
                r["nombre"] == nombre for r in database.get_rutinas_guardadas()
            )
            if nombre_repetido and not messagebox.askyesno(
                "Rutinas", f"«{nombre}» ya existe. ¿Sobrescribirla?",
                parent=dialogo,
            ):
                return
            try:
                database.guardar_rutina_guardada(nombre, False, ejercicios)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo guardar la rutina:\n{error}",
                    parent=dialogo,
                )
                return
            self._mensaje(
                f"Rutina guardada: «{nombre}» ({len(ejercicios)} ejercicios)."
            )
            dialogo.destroy()

        fila_agregar = tk.Frame(dialogo, bg=GRIS_OSCURO)
        fila_agregar.pack(anchor="w", padx=12, pady=(8, 0))
        tk.Button(
            fila_agregar,
            text="＋ AGREGAR EJERCICIO",
            command=agregar,
            font=("Impact", 9),
            fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=10, pady=2, cursor="hand2",
        ).pack(side="left")

        marco_lista = tk.Frame(dialogo, bg=GRIS_OSCURO)
        marco_lista.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        tree.pack(side="left", fill="both", expand=True)
        barra = ttk.Scrollbar(marco_lista, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        pintar_lista()

        fila_final = tk.Frame(dialogo, bg=GRIS_OSCURO)
        fila_final.pack(fill="x", padx=12, pady=(8, 12))
        tk.Button(
            fila_final,
            text="Quitar seleccionado",
            command=quitar,
            font=("Segoe UI", 8, "bold"),
            fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            fila_final,
            text="GUARDAR RUTINA",
            command=guardar,
            font=("Impact", 10),
            fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(side="right")
        tk.Button(
            fila_final,
            text="CANCELAR",
            command=dialogo.destroy,
            font=("Impact", 10),
            fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        dialogo.wait_window()

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
        self.panel_sel = panel_sel
        panel_sel.pack(side="left", fill="y", padx=(0, 6))

        # Plantillas de rutina semanal (patrón del combo "Menú:" de Menús):
        # elegir una abre el cuadro con la semana, las sesiones y aplicar
        tk.Label(
            panel_sel,
            text="Rutina semanal:",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", pady=(0, 2))
        self.combo_plantilla = ttk.Combobox(
            panel_sel,
            values=[p["nombre"] for p in PLANTILLAS_SEMANA],
            state="readonly",
            style="Gym.TCombobox",
        )
        self.combo_plantilla.set(PLACEHOLDER_PLANTILLA)
        self.combo_plantilla.pack(fill="x")
        self.combo_plantilla.bind("<<ComboboxSelected>>", self._al_elegir_plantilla)
        # guarda la semana cargada del paciente como rutina semanal con
        # nombre (aparece en el combo con estrella, junto a las fijas)
        tk.Button(
            panel_sel,
            text="💾 GUARDAR SEMANA",
            command=self._guardar_semana_actual,
            font=("Segoe UI", 8, "bold"),
            fg=NEON,
            bg=GRIS,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        ).pack(fill="x", pady=(5, 0))
        self._refrescar_combo_plantilla()

        self.combo_ej = ttk.Combobox(
            panel_sel, values=[], width=46, state="readonly", style="Gym.TCombobox"
        )
        self.combo_ej.pack(pady=(8, 0))
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
        self.panel_der = panel_der
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
        self.btn_imprimir_rutina = tk.Button(
            acciones,
            text="IMPRIMIR RUTINA",
            command=self._abrir_menu_imprimir,
            font=("Impact", 9),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
        )
        self.btn_imprimir_rutina.pack(fill="x", pady=(6, 0))
        self.menu_imprimir = tk.Menu(self.tree_rutina, tearoff=0, font=("Segoe UI", 9))
        self.menu_imprimir.add_command(
            label="Tabla semanal", command=lambda: self._imprimir_rutina("tabla")
        )
        self.menu_imprimir.add_command(
            label="Descripciones de ejercicios",
            command=lambda: self._imprimir_rutina("descripcion"),
        )
        self.menu_imprimir.add_separator()
        self.menu_imprimir.add_command(
            label="Tabla + descripciones (todo)",
            command=lambda: self._imprimir_rutina("todo"),
        )
        # clic derecho sobre la rutina: editar / quitar el ejercicio;
        # doble clic edita, igual que en Menús
        self.tree_rutina.bind("<Button-3>", self._menu_rutina_contextual)
        self.tree_rutina.bind("<Double-1>", self._editar_ejercicio_rutina)
        # la tabla manda: clic en una fila muestra ese ejercicio en el
        # selector y en la previsualizacion (que viven al fondo)
        self.tree_rutina.bind("<<TreeviewSelect>>", self._al_seleccionar_fila_rutina)
        self.menu_rutina_ctx = tk.Menu(self.tree_rutina, tearoff=0, font=("Segoe UI", 9))
        self.menu_rutina_ctx.add_command(
            label="✏ Editar ejercicio", command=self._editar_ejercicio_rutina
        )
        self.menu_rutina_ctx.add_separator()
        self.menu_rutina_ctx.add_command(
            label="🗑 Quitar de la rutina", command=self._quitar_ejercicio
        )
        self.menu_rutina_ctx.add_command(label="Cancelar")
        self.lbl_rutina_total = ttk.Label(
            acciones, text="0 ejercicios", style="Estado.TLabel"
        )
        self.lbl_rutina_total.pack(anchor="w", pady=(8, 0))
        # la rutina se guarda sola en la BD con cada cambio; este letrero
        # lo hace visible ("Guardada en la BD ✓ HH:MM" tras cada escritura)
        self.lbl_rutina_guardada = ttk.Label(
            acciones,
            text="",
            style="Estado.TLabel",
            font=("Segoe UI", 8),
            foreground=GRIS_TEXTO,
        )
        self.lbl_rutina_guardada.pack(anchor="w")

        # Rutinas guardadas arriba, rutina del paciente debajo y el
        # selector de ejercicio con su previsualizacion al fondo, ligados
        # a la tabla (clic en una fila actualiza combo y previsualizacion)
        self.marco_guardadas = ttk.LabelFrame(
            contenedor_principal,
            text="Rutinas guardadas",
            padding=4,
            style="Gym.TLabelframe",
        )
        self._crear_seccion_rutinas_guardadas(self.marco_guardadas)
        superior.pack(side="bottom", fill="both", expand=True, pady=(6, 0))
        marco_rutina_pac.pack(side="bottom", fill="both", pady=(6, 0))
        self.marco_guardadas.pack(side="bottom", fill="x", pady=(6, 0))

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

    def _al_seleccionar_fila_rutina(self, _event=None):
        """Clic en una fila de la rutina del paciente: lleva el ejercicio
        al selector (cambiando de grupo si hace falta) y la
        previsualizacion muestra su titulo, descripcion e imagen."""
        seleccion = self.tree_rutina.selection()
        if not seleccion or seleccion[0] == "descanso":
            return
        fila = next(
            (r for r in getattr(self, "rutina", [])
             if str(r["id_rutina"]) == seleccion[0]),
            None,
        )
        if not fila:
            return
        grupo = (fila.get("grupo") or "").strip()
        num = str(fila.get("num") or "")
        if grupo and grupo != self.grupo:
            # el combo solo lista el grupo actual: cambia de grupo
            self.grupo_combo.set(
                GRUPOS_ETIQUETAS.get(grupo, grupo.capitalize())
            )
            self._al_cambiar_grupo()
        indice = self._indice_ejercicio_combo(fila, num)
        if indice is not None:
            self.combo_ej.current(indice)
            self._al_seleccionar_combo()
        else:
            # el catalogo cambio y ya no esta: muestra al menos el nombre
            self.lbl_preview_titulo.configure(
                text=f"{fila.get('nombre','')}  |  Equipo: "
                f"{fila.get('equipo') or '-'}"
            )

    def _indice_ejercicio_combo(self, fila, num):
        """Indice del ejercicio de la fila en el combo actual (por num y,
        si el catalogo se renumeró, por nombre)."""
        for indice, ej in enumerate(self.ejercicios):
            if num and str(ej.get("num") or "") == num:
                return indice
        for indice, ej in enumerate(self.ejercicios):
            if fila.get("nombre") and ej.get("nombre") == fila.get("nombre"):
                return indice
        return None

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
            self._marcar_rutina_guardada()
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
        self._marcar_rutina_guardada()
        self._mensaje("Ejercicio quitado de la rutina.")

    def _menu_rutina_contextual(self, event):
        """Clic derecho sobre la rutina (misma lógica que Menús):
        selecciona la fila y ofrece editarla o quitarla (la fila de
        descanso no se edita). El editar también queda al alcance del
        doble clic sobre el ejercicio."""
        fila = self.tree_rutina.identify_row(event.y)
        if not fila or fila == "descanso":
            return "break"
        self.tree_rutina.selection_set(fila)
        self.tree_rutina.focus(fila)
        try:
            self.menu_rutina_ctx.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_rutina_ctx.grab_release()
        return "break"

    def _editar_ejercicio_rutina(self, _event=None):
        """Cuadro para editar la prescripción de un ejercicio de la rutina
        (doble clic o clic derecho > Editar, como el edit de equivalentes
        en Menús). Al guardar, el cambio queda solo en la rutina del
        paciente activo: la plantilla semanal y las rutinas de los demás
        pacientes no se tocan."""
        seleccion = self.tree_rutina.selection()
        if not seleccion or seleccion[0] == "descanso":
            return
        paciente_id = self._paciente_actual()
        id_rutina = int(seleccion[0])
        registro = next(
            (
                r for r in getattr(self, "rutina", [])
                if r.get("id_rutina") == id_rutina
            ),
            None,
        )
        if registro is None or paciente_id is None:
            return

        dialogo = tk.Toplevel(self.marco)
        dialogo.title("Editar ejercicio")
        dialogo.configure(bg=GRIS_OSCURO)
        dialogo.transient(self.marco)
        dialogo.grab_set()

        tk.Label(
            dialogo,
            text=(registro.get("nombre") or "").upper(),
            font=("Impact", 12),
            fg=NEON,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(
            dialogo,
            text=f"{getattr(self, 'dia_actual', '')} · {registro.get('equipo') or '-'}",
            font=("Segoe UI", 8),
            fg=GRIS_TEXTO,
            bg=GRIS_OSCURO,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        campos = (
            ("Series", "series"),
            ("Repeticiones", "repeticiones"),
            ("Descanso entre ejercicios (seg)", "descanso_rep"),
            ("Descanso entre series (seg)", "descanso_series"),
            ("Peso (kg)", "peso"),
        )
        entradas = {}
        for texto, clave in campos:
            f = tk.Frame(dialogo, bg=GRIS_OSCURO)
            f.pack(fill="x", padx=12, pady=2)
            tk.Label(
                f, text=texto, font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO
            ).pack(anchor="w")
            e = ttk.Entry(f, width=14, style="Gym.TEntry")
            e.pack(anchor="w")
            e.insert(0, registro.get(clave) or "")
            entradas[clave] = e

        def guardar():
            datos = {clave: entradas[clave].get().strip() for _, clave in campos}
            if not datos["series"] and not datos["repeticiones"]:
                messagebox.showwarning(
                    "Rutinas", "Indica al menos las series o las repeticiones."
                )
                return
            try:
                database.actualizar_rutina_paciente(id_rutina, paciente_id, datos)
            except Exception as error:
                messagebox.showerror(
                    "Rutinas", f"No se pudo guardar el cambio:\n{error}"
                )
                return
            self._cargar_rutina()
            self._marcar_rutina_guardada()
            self._mensaje(f"Actualizado: {registro.get('nombre')}")
            dialogo.destroy()

        botones = tk.Frame(dialogo, bg=GRIS_OSCURO)
        botones.pack(fill="x", padx=12, pady=(10, 12))
        tk.Button(
            botones,
            text="GUARDAR",
            command=guardar,
            font=("Impact", 10),
            fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(side="left")
        tk.Button(
            botones,
            text="CANCELAR",
            command=dialogo.destroy,
            font=("Impact", 10),
            fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=14, pady=4, cursor="hand2",
        ).pack(side="right")

        dialogo.wait_window()

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
        self._marcar_rutina_guardada()
        self._mensaje("Rutina vaciada.")

    def _abrir_menu_imprimir(self):
        """Despliega las opciones de impresión debajo del botón."""
        boton = self.btn_imprimir_rutina
        self.menu_imprimir.tk_popup(
            boton.winfo_rootx(),
            boton.winfo_rooty() + boton.winfo_height(),
        )

    def _imprimir_rutina(self, modo="todo"):
        """Genera el PDF de la rutina en el modo elegido ("tabla" = solo
        plan semanal y tablas por día; "descripcion" = solo el detalle
        con imagen y descripción; "todo" = ambos) y lo abre."""
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
            rutina_print.generar_pdf_rutina(ruta, paciente, plan, modo=modo)
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

    def _marcar_rutina_guardada(self):
        """Enciende el letrero de guardado tras una escritura exitosa."""
        hora = datetime.now().strftime("%H:%M")
        self.lbl_rutina_guardada.configure(
            text=f"Guardada en la BD ✓ {hora}", foreground=NEON,
        )

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
        # sesión de la plantilla semanal guardada en las notas de las filas
        sesion = next((r.get("notas") for r in filas if r.get("notas")), "")
        if hasattr(self, "marco_rutina_pac"):
            self.marco_rutina_pac.configure(
                text=f"Rutina del paciente · {dia}"
                + (f" · {sesion}" if sesion else "")
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
        # estado neutro del letrero: lo que se ve viene de la BD; los
        # escritos lo encienden en neón con la hora (_marcar_rutina_guardada)
        if hasattr(self, "lbl_rutina_guardada"):
            self.lbl_rutina_guardada.configure(
                text="Guardada en la BD ✓" if semana else "Rutina vacía",
                foreground=GRIS_TEXTO,
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
        self._marcar_rutina_guardada()
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
