"""Calculadora de 1RM — Fuerza (pestaña Rutinas).

Selector de ejercicio común para TODOS los métodos (se puede escribir
cualquiera; los preset son press de banca, sentadilla, peso muerto y
press militar). Diálogo en ramas de árbol con dos grupos:

ESTIMACIÓN POR FÓRMULA (peso + repeticiones → 1RM):
  · Por RPE — Fashi M., Shah Hosseini J., Ahmadi S. (2024).
    "Predicting one repetition maximum in novice males: An RPE-based
    bench press model". Journal of Bodywork & Movement Therapies, 40,
    959-964.
        1RM = ((10 - RPE) / Coef_RPE + 1) x peso levantado
    Coeficientes de la Tabla 1 del artículo (escala CR1-10, RPE >= 5);
    con RPE 10 el peso levantado ES el 1RM. Validada en press de
    banca de varones novatos: en otros ejercicios es aproximación.
  · Por repeticiones — Brzycki 1993:
        1RM = peso / (1.0278 - 0.0278 x repeticiones)
  · Baechle — Baechle & Earle 2000 (NSCA):
        1RM = peso x (1 + 0.033 x repeticiones)
    Protocolo del artículo Rappelt et al. 2024 (Front Physiol
    15:1450732): calentamiento submáximo y fallo entre 1-10 reps.

PROTOCOLOS NSCA (Baechle & Earle, cap. 18; archivo impreso):
  · 1RM directo — protocolo fig. 18.1 con tabla de incrementos por
    tren (superior/inferior); registra el 1RM medido.
  · 10RM submáxima — series de 10 reps hasta el 10RM y
        1RM = 10RM / 0.75   (10RM = 75% del 1RM, cuadro 18.8)
  · Peso por objetivo — con el 1RM y las repeticiones objetivo del
    programa, carga = %1RM x 1RM según el cuadro 18.8
    (1→100, 2→95, 3→93, 4→90, 5→87, 6→85, 7→83, 8→80, 9→77,
     10→75, 12→67, 15→65).

Todo método termina en la tabla de pesos (porcentajes del 1RM o
repeticiones objetivo), con peso exacto y redondeado a discos de
2.5 kg, y el resultado se puede GUARDAR en la BD del paciente activo.
"""
from datetime import datetime

import database

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"
AMARILLO = "#FFD600"
VERDE = "#00E676"

# Tabla 1 del artículo: coeficiente por puntaje RPE (escala CR1-10)
COEFICIENTES_RPE = {
    5: 10.98,
    6: 11.54,
    7: 10.71,
    8: 11.91,
    9: 11.85,
}
# RPE 10: el peso levantado es el 1RM (no se agrega nada)

PORCENTAJES = (50, 55, 60, 65, 70, 75, 80, 85, 90, 95)

# Filas de la tabla de pesos: caben todas si la pantalla es alta; en
# pantallas bajas el diálogo la encoge y queda la barra de scroll.
FILAS_TABLA_MAX = 12
FILAS_TABLA_MIN = 4

# Ejercicios preconfigurados (el selector es editable: se puede
# escribir cualquier otro ejercicio).
EJERCICIOS = (
    "Press de banca", "Sentadilla", "Peso muerto", "Press militar",
)

# Tren del cuerpo por ejercicio: define la tabla de incrementos NSCA.
TREN_EJERCICIO = {
    "Press de banca": "superior",
    "Press militar": "superior",
    "Sentadilla": "inferior",
    "Peso muerto": "inferior",
}

# Cuadro 18.8 (Baechle & Earle, NSCA): % del 1RM según repeticiones.
PCT_POR_REPS = {
    1: 100, 2: 95, 3: 93, 4: 90, 5: 87, 6: 85,
    7: 83, 8: 80, 9: 77, 10: 75, 12: 67, 15: 65,
}

# Tabla de incrementos de carga del protocolo NSCA (fig. 18.1 y 10RM).
INCREMENTOS_NSCA = {
    "1rm": {
        "superior": "aumentos +4 a 9 kg (5-10%) · si falla: -2 a 4 kg (2.5-5%)",
        "inferior": "aumentos +14 a 18 kg (10-20%) · si falla: -7 a 9 kg (5-10%)",
    },
    "10rm": {
        "superior": "aumentos +2 a 4.5 kg (2.5-5%)",
        "inferior": "aumentos +7 a 9 kg (5-10%)",
    },
}

CITA = (
    "Fashi M., Shah Hosseini J., Ahmadi S. (2024). Predicting one "
    "repetition maximum in novice males: An RPE-based bench press "
    "model. J. Bodywork & Movement Therapies, 40, 959-964.\n"
    "Rappelt L.D., Held S., Donath L. (2024). Post-activation "
    "performance enhancement (PAPE) protocols do not further increase "
    "jumping performance beyond warm-up effects. Front. Physiol. "
    "15:1450732 — protocolo y ecuación de Baechle et al. (2000).\n"
    "Baechle T.R., Earle R.W. (eds.). Principios del entrenamiento de "
    "la fuerza y del acondicionamiento físico. NSCA · Ed. Médica "
    "Panamericana, 2007 (2.ª ed.). Cap. 18: fig. 18.1 (p. 409), "
    "pp. 408-409 y cuadro 18.8 (p. 410)."
)

INSTRUCCIONES = """INSTRUCCIONES PARA REALIZAR LA PRUEBA DE 1RM
Press de banca — Fashi et al. (2024)
=====================================

ANTES DEL TEST
--------------
· El test se realiza 3 veces con un intervalo de 48 h entre cada
  ocasión; se promedian los valores.
· Banco y barra libres de discos para el calentamiento.

PASO A PASO (método RPE)
------------------------
1. El paciente descansa sentado 20 minutos en una sala tranquila.
2. Calentamiento: 1 serie de 15 repeticiones solo con la barra
   (sin discos).
3. Muestra al paciente una imagen ampliada de la escala RPE
   (OMNI-RES) y explícala.
4. Realiza UNA repetición de press de banca CON LOS OJOS VENDADOS:
   quitar la visión evita el sesgo mental de ver cuánto peso se
   levanta y hace que la calificación refleje solo la sensación
   del músculo que trabaja.
5. Cadencia fija: bajar la barra en 2 segundos y subirla en
   2 segundos.
6. Inmediatamente después de la repetición, el paciente expresa
   con un número (0-10) la intensidad que sintió en el pectoral.
   Válido para RPE de 5 en adelante (RPE 10 = el peso es su 1RM).
7. La carga del intento se elige entre 60% y 95% de un 1RM
   estimado; el paciente no debe saber qué porcentaje se usó.
8. Descanso de 5 minutos: si el paciente no reconoció la escala,
   se le da otra oportunidad. Se repite el test dos veces y se
   registra el promedio.

MÉTODO POR REPETICIONES (Brzycki)
---------------------------------
· Carga fija elegida por el evaluador; anota el peso y las
  repeticiones logradas con buena técnica.
· Más preciso con 1 a 10 repeticiones.

MÉTODO BAECHLE (NSCA 2000, como lo usó Rappelt et al. 2024)
-----------------------------------------------------------
ESTIMACIÓN (el que alimenta la fórmula):
1. Tres series de calentamiento con cargas submáximas que el
   paciente elige por sí mismo.
2. Series con una carga submáxima buscando el FALLO dentro del
   rango de 1 a 10 repeticiones (1-10RM).
3. Anota el peso y las repeticiones logradas:
      1RM = peso x (1 + 0.033 x repeticiones)
   (entre más cerca del fallo en pocas reps, más preciso).

VERIFICACIÓN DIRECTA (opcional, Estudio III del artículo):
1. Calentamiento: 10 repeticiones solo con la barra.
2. Series progresivas según el 1RM ESTIMADO con Baechle:
      8 reps al 50%  →  4 reps al 60%  →  2 reps al 80%
      →  1 rep al 90%.
3. Aumenta la carga de 0.5 a 5.0 kg por intento hasta que el
   paciente alcance su máximo (1RM) o falle.
4. Para no fatigar la prueba, el 1RM debe alcanzarse a más
   tardar en el 3er o 4o intento de la etapa final.

PROTOCOLO 1RM DIRECTO (NSCA, fig. 18.1 — Baechle & Earle)
---------------------------------------------------------
1. Calentar con cargas ligeras que permitan hacer con facilidad
   entre 5 y 10 repeticiones.
2. Dejar 1 minuto de recuperación.
3. Estimar una carga de calentamiento para 3-5 repeticiones,
   añadiendo el incremento de la tabla.
4. Dejar 2 minutos de recuperación.
5. Estimar, de forma conservadora, una carga para 2-3
   repeticiones, añadiendo el incremento.
6. Dejar entre 2 y 4 minutos de recuperación.
7. Aumentar la carga añadiendo el incremento.
8. Pedir al deportista un intento de 1RM.
9. Si completa una repetición con técnica adecuada: dejar 2-4
   minutos y repetir el paso 7. Si falla: dejar 2-4 minutos,
   bajar la carga según la tabla y repetir el paso 8.
Se continúa así hasta completar una repetición con buena técnica.
Lo ideal: determinar el 1RM en CINCO series o menos.

CUÁNTO PESO AÑADIR O QUITAR (NSCA)
----------------------------------
· Calentamiento y aumentos: tren superior +4 a 9 kg (5-10%);
  tren inferior +14 a 18 kg (10-20%).
· Si falla el intento: tren superior -2 a 4 kg (2.5-5%);
  tren inferior -7 a 9 kg (5-10%).
· Antes de empezar: ayudante junto a la barra para asistir en
  los intentos fallidos; máximo cinco intentos tras el
  calentamiento (la fatiga altera el resultado); rangos
  completos de movimiento y sin trampas.

PRUEBA DE 10RM SUBMÁXIMA (NSCA, cuadro 18.8)
--------------------------------------------
Alternativa cuando no se puede (o no conviene) hacer una prueba
de fuerza máxima. Apropiada para casi todos los deportistas si
ejecutan el ejercicio con técnica correcta.
1. Calentar con cargas ligeras (5-10 reps fáciles) y al menos
   dos series de calentamiento con más peso.
2. Realizar series de 10 repeticiones (no de 1) y aumentar la
   carga con incrementos de la MITAD de los de la prueba de
   1RM: +2 a 4.5 kg (2.5-5%) tren superior; +7 a 9 kg (5-10%)
   tren inferior.
3. Continuar hasta encontrar la carga que permita hacer SOLO
   10 repeticiones.
4. Determinar el 10RM en cinco series o menos: el calentamiento
   excesivo y las series acumuladas fatigan y comprometen la
   precisión.
5. Estimar el 1RM: 10RM = 75% del 1RM, es decir
      1RM = 10RM / 0.75
   Ejemplo del libro: 10RM de 135 kg → 1RM de 180 kg.
Nota: los ejercicios de potencia no son apropiados para pruebas
de múltiples RM (la técnica se deteriora con la fatiga).

PESO POR OBJETIVO (NSCA, cuadro 18.8)
-------------------------------------
El preparador fija primero las repeticiones que usará el
programa y la prueba determina la carga de ese RM.
1. Elegir las repeticiones objetivo del programa (ej. 6 reps en
   press de banca).
2. Incluir en la prueba series de ese mismo RM (series de 6RM),
   con la misma mecánica de calentamiento e incrementos de la
   prueba de 1RM.
3. Usar ejercicios básicos y complementarios según el objetivo;
   con nivel técnico suficiente se pueden hacer determinaciones
   de múltiples RM con menos reps y cargas más altas.
4. Determinar la carga objetivo en cinco series o menos y
   aplicarla al programa.
Tabla de referencia (reps → % del 1RM):
 1→100 · 2→95 · 3→93 · 4→90 · 5→87 · 6→85 · 7→83 · 8→80
 9→77 · 10→75 · 12→67 · 15→65
Ejemplo: 1RM de 100 kg y objetivo de 8 reps → 80% → 80 kg.
La relación % 1RM-reps varía entre personas y ejercicios: la
tabla es una guía.

PROTOCOLO ESTANDARIZADO (STP, referencia clásica)
-------------------------------------------------
· Se aumenta el peso tras cada intento exitoso hasta que falle.
· Descanso de 1 minuto entre intentos; el 1RM se alcanza dentro
  de 5 intentos.

NOTAS
-----
· La ecuación RPE fue validada en press de banca de varones sin
  experiencia previa (novatos): en otros ejercicios úsala como
  aproximación y compara con otro método.
· Brzycki y Baechle son ecuaciones genéricas: aplican a los
  básicos (banca, sentadilla, peso muerto, press militar...).
  Baechle y Brzycki coinciden en el punto de 10 reps (≈75%).
· Registra siempre el resultado en la BD del paciente con el
  botón GUARDAR.
"""


def uno_rm_por_rpe(peso, rpe):
    """1RM con la ecuación RPE del artículo (Fashi et al., 2024)."""
    rpe = int(rpe)
    if rpe >= 10:
        return float(peso)
    coef = COEFICIENTES_RPE.get(rpe)
    if not coef:
        raise ValueError("RPE fuera de rango (5-10).")
    return float(peso) * ((10 - rpe) / coef + 1)


def uno_rm_por_repeticiones(peso, reps):
    """1RM con la ecuación de Brzycki (1993), tal como la cita el
    artículo para su protocolo de validación."""
    reps = int(reps)
    if not 1 <= reps <= 20:
        raise ValueError("Repeticiones fuera de rango (1-20).")
    return float(peso) / (1.0278 - 0.0278 * reps)


def uno_rm_baechle(peso, reps):
    """1RM con la ecuación de Baechle & Earle 2000 (NSCA), la que
    usó Rappelt et al. 2024: prueba al fallo entre 1-10 repeticiones.
        1RM = peso x (1 + 0.033 x repeticiones)"""
    reps = int(reps)
    if not 1 <= reps <= 10:
        raise ValueError(
            "Baechle se usa al fallo entre 1 y 10 repeticiones "
            "(rango del protocolo)."
        )
    return float(peso) * (1 + 0.033 * reps)


def uno_rm_desde_10rm(peso):
    """1RM desde la prueba submáxima de 10RM (NSCA, cuadro 18.8):
    10RM = 75% del 1RM, es decir 1RM = 10RM / 0.75."""
    return float(peso) / (PCT_POR_REPS[10] / 100.0)


def carga_por_objetivo(uno_rm, reps):
    """Carga de entrenamiento para las repeticiones objetivo según el
    cuadro 18.8 (NSCA): carga = %1RM x 1RM. Devuelve (carga, pct)."""
    reps = int(reps)
    pct = PCT_POR_REPS.get(reps)
    if pct is None:
        raise ValueError(
            "Repeticiones fuera del cuadro 18.8 (1-10, 12 o 15)."
        )
    return float(uno_rm) * pct / 100.0, pct


def _a_float(texto):
    return float(str(texto).strip().replace(",", "."))


def _redondear_discos(kg, incremento=2.5):
    """Redondea al disco cargable más cercano (2.5 kg por defecto)."""
    return round(kg / incremento) * incremento


def abrir_dialogo_1rm(parent, app=None):
    """Ventana con ramas de árbol: métodos de 1RM para press de banca.

    `app` es la ventana principal: se usa para tomar el paciente activo
    al guardar el resultado.
    """
    import tkinter as tk
    from tkinter import messagebox, ttk

    dialogo = tk.Toplevel(parent)
    dialogo.title("1RM · Calculadora de fuerza")
    dialogo.configure(bg=NEGRO)
    dialogo.transient(parent)
    dialogo.grab_set()
    dialogo.resizable(False, False)
    try:
        dialogo.iconbitmap("icono_app.ico")
    except Exception:
        pass

    # ------------------------------------------------ barra de título
    encabezado = tk.Frame(dialogo, bg=NEGRO, padx=14, pady=10)
    encabezado.pack(fill="x")
    tk.Label(
        encabezado, text="🏋 CALCULADORA 1RM", font=("Impact", 16),
        fg=NEON, bg=NEGRO,
    ).pack(side="left")
    lbl_ejercicio = tk.Label(
        encabezado, text=EJERCICIOS[0].upper(), font=("Impact", 16),
        fg=NARANJA, bg=NEGRO,
    )
    lbl_ejercicio.pack(side="left", padx=(10, 0))

    cuerpo = tk.Frame(dialogo, bg=GRIS_OSCURO)
    cuerpo.pack(fill="both", expand=True)

    # ------------------------------------------------ ramas de árbol
    marco_arbol = tk.LabelFrame(
        cuerpo, bg=GRIS_OSCURO, fg=NEON, text=" Métodos ",
        font=("Segoe UI", 9, "bold"), padx=8, pady=8,
    )
    marco_arbol.pack(side="left", fill="y", padx=(12, 6), pady=12)

    arbol = ttk.Treeview(marco_arbol, show="tree", selectmode="browse",
                         height=9)
    estilo = ttk.Style(dialogo)
    estilo.theme_use("clam")
    estilo.configure("R1.Treeview", background=GRIS_OSCURO,
                     fieldbackground=GRIS_OSCURO, foreground=BLANCO,
                     rowheight=26, borderwidth=0, font=("Segoe UI", 10))
    estilo.map("R1.Treeview", background=[("selected", NARANJA)],
               foreground=[("selected", NEGRO)])
    arbol.configure(style="R1.Treeview")
    arbol.column("#0", width=230)
    grupo_formulas = arbol.insert("", "end", iid="formulas", open=True,
                                  text="📐 Estimación por fórmula")
    arbol.insert(grupo_formulas, "end", iid="rpe",
                 text="Por RPE (Fashi 2024)")
    arbol.insert(grupo_formulas, "end", iid="reps",
                 text="Por repeticiones (Brzycki)")
    arbol.insert(grupo_formulas, "end", iid="baechle",
                 text="Baechle (NSCA 2000)")
    grupo_nsca = arbol.insert("", "end", iid="nsca", open=True,
                              text="📋 Protocolos NSCA")
    arbol.insert(grupo_nsca, "end", iid="directo",
                 text="1RM directo (fig. 18.1)")
    arbol.insert(grupo_nsca, "end", iid="diez",
                 text="10RM submáxima")
    arbol.insert(grupo_nsca, "end", iid="objetivo",
                 text="Peso por objetivo")
    arbol.pack(fill="both", expand=True)

    tk.Label(
        marco_arbol, text="Elige un método; el ejercicio de arriba "
        "aplica a todos", font=("Segoe UI", 8),
        fg=GRIS_TEXTO, bg=GRIS_OSCURO, wraplength=220, justify="left",
    ).pack(anchor="w", pady=(8, 0))

    def ver_instrucciones():
        ventana = tk.Toplevel(dialogo)
        ventana.title("Instrucciones · prueba de 1RM")
        ventana.configure(bg=GRIS_OSCURO)
        ventana.transient(dialogo)
        try:
            ventana.iconbitmap("icono_app.ico")
        except Exception:
            pass
        texto = tk.Text(
            ventana, bg=GRIS_OSCURO, fg=BLANCO, relief="flat",
            font=("Consolas", 9), wrap="word", width=62, height=30,
            padx=12, pady=10, insertbackground=BLANCO,
        )
        texto.pack(side="left", fill="both", expand=True)
        barra_sc = tk.Scrollbar(ventana, command=texto.yview)
        barra_sc.pack(side="right", fill="y")
        texto.configure(yscrollcommand=barra_sc.set)
        texto.insert("1.0", INSTRUCCIONES)
        texto.configure(state="disabled")
        tk.Button(
            ventana, text="CERRAR", command=ventana.destroy,
            font=("Impact", 11), fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side="bottom", pady=(0, 8))
        ventana.update_idletasks()
        x = max(0, (ventana.winfo_screenwidth()
                    - ventana.winfo_width()) // 2)
        y = max(0, (ventana.winfo_screenheight()
                    - ventana.winfo_height()) // 2)
        ventana.geometry(f"+{x}+{y}")

    tk.Button(
        marco_arbol, text="📋 INSTRUCCIONES DE LA PRUEBA",
        command=ver_instrucciones,
        font=("Segoe UI", 9, "bold"), fg=NEGRO, bg=GRIS,
        activebackground=NARANJA, activeforeground=BLANCO,
        relief="flat", padx=8, pady=4, cursor="hand2",
    ).pack(fill="x", pady=(10, 0))

    # ------------------------------------------------ panel derecho
    derecha = tk.Frame(cuerpo, bg=GRIS_OSCURO)
    derecha.pack(side="left", fill="both", expand=True, padx=(6, 12),
                 pady=12)

    # ----- selector de ejercicio, común a todos los métodos -----
    selector = tk.Frame(derecha, bg=GRIS_OSCURO)
    selector.pack(fill="x")
    tk.Label(
        selector, text="Ejercicio:", width=24, anchor="e",
        font=("Segoe UI", 10, "bold"), fg=BLANCO, bg=GRIS_OSCURO,
    ).pack(side="left")
    combo_ejercicio = ttk.Combobox(
        selector, values=list(EJERCICIOS), state="normal", width=18,
    )
    combo_ejercicio.set(EJERCICIOS[0])
    combo_ejercicio.pack(side="left", padx=(8, 0), ipady=3)
    tk.Label(
        derecha,
        text="Aplica a todos los métodos y se guarda con el resultado.",
        font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        wraplength=380, justify="left",
    ).pack(anchor="w", pady=(2, 6))

    # ----- formulario RPE -----
    form_rpe = tk.Frame(derecha, bg=GRIS_OSCURO)

    def _caja(marco, etiqueta, ancho=12):
        fila = tk.Frame(marco, bg=GRIS_OSCURO)
        fila.pack(fill="x", pady=4)
        tk.Label(fila, text=etiqueta, width=24, anchor="e",
                 font=("Segoe UI", 10, "bold"), fg=BLANCO,
                 bg=GRIS_OSCURO).pack(side="left")
        entrada = tk.Entry(fila, width=ancho, bg=GRIS, fg=BLANCO,
                           insertbackground=NEON, relief="flat",
                           justify="center", font=("Segoe UI", 11))
        entrada.pack(side="left", padx=(8, 0), ipady=3)
        return entrada

    entrada_rpe_peso = _caja(form_rpe, "Peso levantado (kg):")
    fila_rpe = tk.Frame(form_rpe, bg=GRIS_OSCURO)
    fila_rpe.pack(fill="x", pady=4)
    tk.Label(fila_rpe, text="RPE (escala CR1-10):", width=24, anchor="e",
             font=("Segoe UI", 10, "bold"), fg=BLANCO,
             bg=GRIS_OSCURO).pack(side="left")
    combo_rpe = ttk.Combobox(fila_rpe, values=("5", "6", "7", "8", "9",
                                               "10"),
                             state="readonly", width=8)
    combo_rpe.set("8")
    combo_rpe.pack(side="left", padx=(8, 0), ipady=3)
    tk.Label(
        form_rpe,
        text="RPE 8 = pudo levantar 2 más · RPE 9 = 1 más · RPE 10 = "
             "máximo (el peso es su 1RM). Solo válido para RPE de 5 en "
             "adelante (Fashi et al., 2024). Ecuación validada en press "
             "de banca de novatos: en otros ejercicios es aproximación.",
        font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        wraplength=380, justify="left",
    ).pack(anchor="w", pady=(6, 0))

    # ----- formulario Brzycki -----
    form_reps = tk.Frame(derecha, bg=GRIS_OSCURO)
    entrada_reps_peso = _caja(form_reps, "Peso levantado (kg):")
    entrada_reps = _caja(form_reps, "Repeticiones logradas:")
    tk.Label(
        form_reps,
        text="1RM = peso / (1.0278 - 0.0278 x reps). Más preciso con "
             "1-10 repeticiones. Es el protocolo con el que el artículo "
             "validó su ecuación RPE.",
        font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        wraplength=380, justify="left",
    ).pack(anchor="w", pady=(6, 0))

    # ----- formulario Baechle -----
    form_bae = tk.Frame(derecha, bg=GRIS_OSCURO)
    entrada_bae_peso = _caja(form_bae, "Peso levantado (kg):")
    entrada_bae_reps = _caja(form_bae, "Repeticiones al fallo:")
    tk.Label(
        form_bae,
        text="1RM = peso x (1 + 0.033 x reps). Protocolo: 3 series de "
             "calentamiento submáximas y prueba al FALLO entre 1-10 "
             "repeticiones (Baechle & Earle 2000; Rappelt et al. 2024). "
             "Con más de 10 reps pierde precisión.",
        font=("Segoe UI", 8), fg=GRIS_TEXTO, bg=GRIS_OSCURO,
        wraplength=380, justify="left",
    ).pack(anchor="w", pady=(6, 0))

    def _nota(marco, texto, color=GRIS_TEXTO):
        etiqueta = tk.Label(
            marco, text=texto, font=("Segoe UI", 8), fg=color,
            bg=GRIS_OSCURO, wraplength=380, justify="left",
        )
        etiqueta.pack(anchor="w", pady=(6, 0))
        return etiqueta

    # ----- formulario 1RM directo (NSCA, fig. 18.1) -----
    form_directo = tk.Frame(derecha, bg=GRIS_OSCURO)
    entrada_dir_peso = _caja(form_directo, "Peso del 1RM logrado (kg):")
    _nota(
        form_directo,
        "Registra el 1RM medido con el protocolo NSCA: una repetición "
        "completa con buena técnica, en cinco series o menos (pasos en "
        "INSTRUCCIONES DE LA PRUEBA).",
    )
    lbl_dir_incrementos = _nota(form_directo, "", color=NEON)

    # ----- formulario 10RM submáxima (NSCA, cuadro 18.8) -----
    form_diez = tk.Frame(derecha, bg=GRIS_OSCURO)
    entrada_diez_peso = _caja(form_diez, "Peso del 10RM (kg):")
    _nota(
        form_diez,
        "1RM = 10RM / 0.75 (10RM = 75% del 1RM). Carga con la que "
        "completa SOLO 10 repeticiones, hallada en cinco series o "
        "menos. Ejemplo del libro: 10RM de 135 kg → 1RM de 180 kg.",
    )
    lbl_diez_incrementos = _nota(form_diez, "", color=NEON)

    # ----- formulario peso por objetivo (NSCA, cuadro 18.8) -----
    form_obj = tk.Frame(derecha, bg=GRIS_OSCURO)
    entrada_obj_1rm = _caja(form_obj, "1RM del deportista (kg):")
    fila_obj = tk.Frame(form_obj, bg=GRIS_OSCURO)
    fila_obj.pack(fill="x", pady=4)
    tk.Label(fila_obj, text="Repeticiones objetivo:", width=24,
             anchor="e", font=("Segoe UI", 10, "bold"), fg=BLANCO,
             bg=GRIS_OSCURO).pack(side="left")
    combo_obj_reps = ttk.Combobox(
        fila_obj, values=[str(r) for r in PCT_POR_REPS],
        state="readonly", width=8,
    )
    combo_obj_reps.set("8")
    combo_obj_reps.pack(side="left", padx=(8, 0), ipady=3)
    _nota(
        form_obj,
        "Carga = % del 1RM x 1RM según las repeticiones del programa "
        "(cuadro 18.8). Al calcular con otro método, el 1RM se copia "
        "aquí. La relación % - reps varía entre personas y ejercicios: "
        "es una guía.",
    )

    # ----- resultado -----
    lbl_1rm = tk.Label(
        derecha, text="1RM ESTIMADO: —", font=("Impact", 20),
        fg=AMARILLO, bg=GRIS_OSCURO, wraplength=400, justify="left",
    )
    lbl_1rm.pack(anchor="w", pady=(14, 2))

    columnas = ("pct", "exacto", "discos")
    marco_tabla = tk.Frame(derecha, bg=GRIS_OSCURO)
    marco_tabla.pack(fill="both", expand=True, pady=(6, 0))
    tabla = ttk.Treeview(marco_tabla, columns=columnas, show="headings",
                         height=FILAS_TABLA_MAX)
    estilo.configure("R2.Treeview", background=GRIS_OSCURO,
                     fieldbackground=GRIS_OSCURO, foreground=BLANCO,
                     rowheight=22, borderwidth=0)
    estilo.configure("R2.Treeview.Heading", background=GRIS, fg=NEON,
                     font=("Segoe UI", 9, "bold"))
    tabla.configure(style="R2.Treeview")
    for col, texto, ancho, ancla in (
        ("pct", "% 1RM", 100, "center"),
        ("exacto", "Peso (kg)", 115, "center"),
        ("discos", "A cargar (discos 2.5 kg)", 170, "center"),
    ):
        tabla.heading(col, text=texto)
        tabla.column(col, width=ancho, anchor=ancla)
    barra_tabla = ttk.Scrollbar(marco_tabla, orient="vertical",
                                command=tabla.yview)
    tabla.configure(yscrollcommand=barra_tabla.set)
    barra_tabla.pack(side="right", fill="y")
    tabla.pack(side="left", fill="both", expand=True)
    tabla.tag_configure("fuerte", foreground=AMARILLO)

    # cita del artículo
    tk.Label(
        dialogo, text=CITA, font=("Segoe UI", 7), fg=GRIS_TEXTO, bg=NEGRO,
        wraplength=640, justify="left",
    ).pack(anchor="w", padx=14, pady=(0, 8))

    # ------------------------------------------------ lógica
    formularios = {
        "rpe": form_rpe,
        "reps": form_reps,
        "baechle": form_bae,
        "directo": form_directo,
        "diez": form_diez,
        "objetivo": form_obj,
    }

    def _rama_elegida():
        """Método elegido; None si la selección es un grupo del árbol."""
        sel = arbol.selection()
        return sel[0] if sel and sel[0] in formularios else None

    def _mostrar_formulario():
        rama = _rama_elegida()
        for marco in formularios.values():
            marco.pack_forget()
        if rama:
            # arriba del resultado: primero se captura, luego se lee
            formularios[rama].pack(fill="x", before=lbl_1rm)

    def _texto_incrementos(prueba):
        tren = TREN_EJERCICIO.get(combo_ejercicio.get().strip())
        tabla_inc = INCREMENTOS_NSCA[prueba]
        if tren:
            return f"Incrementos NSCA (tren {tren}): {tabla_inc[tren]}"
        return (
            f"Incrementos NSCA — tren superior: {tabla_inc['superior']} "
            f"| tren inferior: {tabla_inc['inferior']}"
        )

    def _ajustar_alto():
        """Encoge la tabla si el diálogo completo no cabe en pantalla."""
        disponible = dialogo.winfo_screenheight() - 110
        filas = FILAS_TABLA_MAX
        tabla.configure(height=filas)
        dialogo.update_idletasks()
        while (filas > FILAS_TABLA_MIN
               and dialogo.winfo_reqheight() > disponible):
            filas -= 1
            tabla.configure(height=filas)
            dialogo.update_idletasks()

    def _al_cambiar_ejercicio(_evento=None):
        ejercicio = combo_ejercicio.get().strip()
        lbl_ejercicio.configure(text=ejercicio.upper() or "EJERCICIO")
        lbl_dir_incrementos.configure(text=_texto_incrementos("1rm"))
        lbl_diez_incrementos.configure(text=_texto_incrementos("10rm"))
        _ajustar_alto()

    def _poner_titulo(texto):
        """Título del resultado: reduce la fuente hasta caber en una línea."""
        from tkinter import font as tkfont
        tam = 20
        while tam > 12 and tkfont.Font(
            family="Impact", size=tam
        ).measure(texto) > 400:
            tam -= 2
        lbl_1rm.configure(text=texto, font=("Impact", tam))

    def _kg(entrada, nombre):
        try:
            valor = _a_float(entrada.get())
        except ValueError:
            raise ValueError(f"{nombre} debe ser un número.")
        if valor <= 0:
            raise ValueError(f"{nombre} debe ser mayor a 0.")
        return valor

    def _entero(texto, nombre):
        try:
            return int(str(texto).strip())
        except ValueError:
            raise ValueError(f"{nombre} debe ser un número entero.")

    resultado_ultimo = {"datos": None}

    def calcular():
        rama = _rama_elegida()
        if rama is None:
            messagebox.showwarning(
                "1RM", "Elige primero un método del árbol.", parent=dialogo
            )
            return
        ejercicio = combo_ejercicio.get().strip()
        if not ejercicio:
            messagebox.showwarning(
                "1RM", "Elige o escribe el ejercicio.", parent=dialogo
            )
            return
        rpe = reps = pct_objetivo = None
        try:
            if rama == "rpe":
                peso = _kg(entrada_rpe_peso, "El peso")
                rpe = _entero(combo_rpe.get(), "El RPE")
                uno_rm = uno_rm_por_rpe(peso, rpe)
                metodo = "RPE (Fashi et al., 2024)"
            elif rama == "reps":
                peso = _kg(entrada_reps_peso, "El peso")
                reps = _entero(entrada_reps.get(), "Las repeticiones")
                uno_rm = uno_rm_por_repeticiones(peso, reps)
                metodo = "Repeticiones (Brzycki)"
            elif rama == "baechle":
                peso = _kg(entrada_bae_peso, "El peso")
                reps = _entero(entrada_bae_reps.get(), "Las repeticiones")
                uno_rm = uno_rm_baechle(peso, reps)
                metodo = "Baechle (NSCA 2000)"
            elif rama == "directo":
                peso = _kg(entrada_dir_peso, "El peso del 1RM")
                reps = 1
                uno_rm = peso
                metodo = "1RM directo (NSCA)"
            elif rama == "diez":
                peso = _kg(entrada_diez_peso, "El peso del 10RM")
                reps = 10
                uno_rm = uno_rm_desde_10rm(peso)
                metodo = "10RM submáxima (NSCA)"
            else:
                uno_rm = _kg(entrada_obj_1rm, "El 1RM")
                reps = _entero(combo_obj_reps.get(), "Las repeticiones")
                peso, pct_objetivo = carga_por_objetivo(uno_rm, reps)
                metodo = "Peso por objetivo (NSCA)"
        except ValueError as error:
            messagebox.showwarning("1RM", str(error), parent=dialogo)
            return

        # peso x repeticiones <-> resultado (1RM); en "objetivo" el peso
        # es la carga de entrenamiento para esas repeticiones.
        resultado_ultimo["datos"] = {
            "ejercicio": ejercicio,
            "metodo": metodo,
            "peso": round(peso, 1),
            "rpe": rpe,
            "repeticiones": reps,
            "resultado": round(uno_rm, 1),
        }

        nombre = ejercicio.upper()
        for item in tabla.get_children():
            tabla.delete(item)
        if rama == "objetivo":
            _poner_titulo(
                f"CARGA {nombre} · {reps} REPS ({pct_objetivo}%): "
                f"{peso:.1f} kg"
            )
            destacado = None
            for reps_fila, pct in PCT_POR_REPS.items():
                kg = uno_rm * pct / 100.0
                etiqueta_fila = (
                    f"{reps_fila} rep · {pct}%"
                    if reps_fila == 1 else f"{reps_fila} reps · {pct}%"
                )
                item = tabla.insert(
                    "", "end",
                    values=(etiqueta_fila, f"{kg:.1f} kg",
                            f"{_redondear_discos(kg):g} kg"),
                    tags=("fuerte" if reps_fila == reps else "",),
                )
                if reps_fila == reps:
                    destacado = item
            if destacado:
                tabla.see(destacado)
            _ajustar_alto()
            return

        etiqueta = "1RM DIRECTO" if rama == "directo" else "1RM ESTIMADO"
        _poner_titulo(f"{etiqueta} {nombre}: {uno_rm:.1f} kg")
        # deja el 1RM listo para calcular el peso por objetivo
        entrada_obj_1rm.delete(0, "end")
        entrada_obj_1rm.insert(0, f"{uno_rm:.1f}")
        for pct in PORCENTAJES:
            kg = uno_rm * pct / 100.0
            fuerte = "fuerte" if pct in (80, 85, 90) else ""
            tabla.insert(
                "", "end",
                values=(f"{pct}%", f"{kg:.1f} kg",
                        f"{_redondear_discos(kg):g} kg"),
                tags=(fuerte,),
            )
        _ajustar_alto()

    def guardar():
        datos = resultado_ultimo["datos"]
        if not datos:
            messagebox.showwarning(
                "1RM",
                "Primero calcula el 1RM antes de guardar.",
                parent=dialogo,
            )
            return
        paciente_id = getattr(app, "id_paciente_antro", None) if app else None
        if paciente_id is None:
            messagebox.showwarning(
                "1RM",
                "Selecciona un paciente antes de guardar.",
                parent=dialogo,
            )
            return
        database.insert_uno_rm(
            dict(
                datos,
                paciente_id=paciente_id,
                fecha=datetime.now().strftime("%Y-%m-%d"),
            )
        )
        if datos["metodo"].startswith("Peso por objetivo"):
            texto = (
                f"Registro de {datos['ejercicio']} guardado para el "
                f"paciente activo: 1RM de {datos['resultado']} kg → "
                f"carga de {datos['peso']} kg para "
                f"{datos['repeticiones']} repeticiones."
            )
        else:
            texto = (
                f"1RM de {datos['ejercicio']} ({datos['resultado']} kg, "
                f"método {datos['metodo']}) guardado para el paciente "
                f"activo."
            )
        messagebox.showinfo("1RM", texto, parent=dialogo)

    barra = tk.Frame(derecha, bg=GRIS_OSCURO)
    barra.pack(fill="x", pady=(10, 0))
    tk.Button(
        barra, text="CALCULAR 1RM", command=calcular, font=("Impact", 13),
        fg=NEGRO, bg=NEON, activebackground=NARANJA, activeforeground=NEGRO,
        relief="flat", padx=16, pady=6, cursor="hand2",
    ).pack(side="left", padx=(0, 8))
    tk.Button(
        barra, text="💾 GUARDAR", command=guardar, font=("Impact", 13),
        fg=NEGRO, bg=NARANJA, activebackground=NEON, activeforeground=NEGRO,
        relief="flat", padx=16, pady=6, cursor="hand2",
    ).pack(side="left", padx=(0, 8))
    tk.Button(
        barra, text="LIMPIAR", command=lambda: (
            _poner_titulo("1RM ESTIMADO: —"),
            resultado_ultimo.update({"datos": None}),
            *[tabla.delete(i) for i in tabla.get_children()],
        ),
        font=("Impact", 13), fg=NEON, bg=GRIS,
        activebackground=NARANJA, activeforeground=BLANCO,
        relief="flat", padx=16, pady=6, cursor="hand2",
    ).pack(side="left")

    arbol.bind("<<TreeviewSelect>>", lambda _e: _mostrar_formulario())
    combo_ejercicio.bind("<<ComboboxSelected>>", _al_cambiar_ejercicio)
    combo_ejercicio.bind("<KeyRelease>", _al_cambiar_ejercicio)

    # rama inicial
    arbol.selection_set("rpe")
    _mostrar_formulario()
    _al_cambiar_ejercicio()

    # centrado, dejando la ventana por encima de la barra de tareas
    dialogo.update_idletasks()
    ancho = dialogo.winfo_reqwidth()
    alto_maximo = dialogo.winfo_screenheight() - 110
    alto_previsto = min(dialogo.winfo_reqheight() + 60, alto_maximo)
    x = max(0, (dialogo.winfo_screenwidth() - ancho) // 2)
    y = max(0, (dialogo.winfo_screenheight() - 70 - alto_previsto) // 2)
    dialogo.geometry(f"+{x}+{y}")
    dialogo.wait_window(dialogo)
    # último cálculo (o None): la pestaña Rutinas lo usa como 1RM de
    # referencia para llenar el peso por porcentaje
    return resultado_ultimo["datos"]
