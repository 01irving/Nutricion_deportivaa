"""Calculadora de 1RM — Press de banca (pestaña Rutinas).

Diálogo en ramas de árbol con dos métodos, según el artículo:
  · Por RPE — Fashi M., Shah Hosseini J., Ahmadi S. (2024).
    "Predicting one repetition maximum in novice males: An RPE-based
    bench press model". Journal of Bodywork & Movement Therapies, 40,
    959-964.
        1RM = ((10 - RPE) / Coef_RPE + 1) x peso levantado
    Coeficientes de la Tabla 1 del artículo (escala CR1-10, RPE >= 5);
    con RPE 10 el peso levantado ES el 1RM.
  · Por repeticiones — Brzycki 1993 (protocolo con el que el artículo
    validó su ecuación):
        1RM = peso / (1.0278 - 0.0278 x repeticiones)

Ambos métodos terminan en la tabla de porcentajes del 1RM (50-95%),
con el peso exacto y el redondeado a discos de 2.5 kg, y el resultado
se puede GUARDAR en la BD para el paciente activo. El diálogo incluye
las instrucciones para realizar la prueba según el artículo.
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

CITA = (
    "Fashi M., Shah Hosseini J., Ahmadi S. (2024). Predicting one "
    "repetition maximum in novice males: An RPE-based bench press "
    "model. J. Bodywork & Movement Therapies, 40, 959-964."
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

PROTOCOLO ESTANDARIZADO (STP, referencia clásica)
-------------------------------------------------
· Se aumenta el peso tras cada intento exitoso hasta que falle.
· Descanso de 1 minuto entre intentos; el 1RM se alcanza dentro
  de 5 intentos.

NOTAS
-----
· La ecuación RPE fue validada en varones sin experiencia previa
  en pesas (novatos); interpola con criterio en atletas
  avanzados.
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
    dialogo.title("1RM · Press de banca")
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
    tk.Label(
        encabezado, text="PRESS DE BANCA", font=("Impact", 16),
        fg=NARANJA, bg=NEGRO,
    ).pack(side="left", padx=(10, 0))

    cuerpo = tk.Frame(dialogo, bg=GRIS_OSCURO)
    cuerpo.pack(fill="both", expand=True)

    # ------------------------------------------------ ramas de árbol
    marco_arbol = tk.LabelFrame(
        cuerpo, bg=GRIS_OSCURO, fg=NEON, text=" Métodos ",
        font=("Segoe UI", 9, "bold"), padx=8, pady=8,
    )
    marco_arbol.pack(side="left", fill="y", padx=(12, 6), pady=12)

    arbol = ttk.Treeview(marco_arbol, show="tree", selectmode="browse",
                         height=6)
    estilo = ttk.Style(dialogo)
    estilo.theme_use("clam")
    estilo.configure("R1.Treeview", background=GRIS_OSCURO,
                     fieldbackground=GRIS_OSCURO, foreground=BLANCO,
                     rowheight=26, borderwidth=0, font=("Segoe UI", 10))
    estilo.map("R1.Treeview", background=[("selected", NARANJA)],
               foreground=[("selected", NEGRO)])
    arbol.configure(style="R1.Treeview")
    raiz = arbol.insert("", "end", iid="raiz", open=True,
                        text="🏋 Press de banca")
    arbol.insert(raiz, "end", iid="rpe",
                 text="Por RPE (Fashi 2024)")
    arbol.insert(raiz, "end", iid="reps",
                 text="Por repeticiones (Brzycki)")
    arbol.pack(fill="both", expand=True)

    tk.Label(
        marco_arbol, text="Elige una rama del árbol", font=("Segoe UI", 8),
        fg=GRIS_TEXTO, bg=GRIS_OSCURO, wraplength=190,
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
             "adelante (Fashi et al., 2024).",
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

    # ----- resultado -----
    lbl_1rm = tk.Label(
        derecha, text="1RM ESTIMADO: —", font=("Impact", 20),
        fg=AMARILLO, bg=GRIS_OSCURO,
    )
    lbl_1rm.pack(anchor="w", pady=(14, 2))

    columnas = ("pct", "exacto", "discos")
    tabla = ttk.Treeview(derecha, columns=columnas, show="headings",
                         height=8)
    estilo.configure("R2.Treeview", background=GRIS_OSCURO,
                     fieldbackground=GRIS_OSCURO, foreground=BLANCO,
                     rowheight=22, borderwidth=0)
    estilo.configure("R2.Treeview.Heading", background=GRIS, fg=NEON,
                     font=("Segoe UI", 9, "bold"))
    tabla.configure(style="R2.Treeview")
    for col, texto, ancho, ancla in (
        ("pct", "% 1RM", 90, "center"),
        ("exacto", "Peso (kg)", 120, "center"),
        ("discos", "A cargar (discos 2.5 kg)", 190, "center"),
    ):
        tabla.heading(col, text=texto)
        tabla.column(col, width=ancho, anchor=ancla)
    tabla.pack(fill="both", expand=True, pady=(6, 0))
    tabla.tag_configure("fuerte", foreground=AMARILLO)

    # cita del artículo
    tk.Label(
        dialogo, text=CITA, font=("Segoe UI", 7), fg=GRIS_TEXTO, bg=NEGRO,
        wraplength=640, justify="left",
    ).pack(anchor="w", padx=14, pady=(0, 8))

    # ------------------------------------------------ lógica
    def _rama_elegida():
        sel = arbol.selection()
        return sel[0] if sel else None

    def _mostrar_formulario():
        rama = _rama_elegida()
        for marco in (form_rpe, form_reps):
            marco.pack_forget()
        if rama == "rpe":
            form_rpe.pack(fill="x")
        elif rama == "reps":
            form_reps.pack(fill="x")

    resultado_ultimo = {"datos": None}

    def calcular():
        rama = _rama_elegida()
        if rama is None:
            messagebox.showwarning(
                "1RM", "Elige primero una rama del árbol.", parent=dialogo
            )
            return
        try:
            peso = _a_float(
                entrada_rpe_peso.get() if rama == "rpe"
                else entrada_reps_peso.get()
            )
        except ValueError:
            messagebox.showwarning(
                "1RM", "El peso debe ser un número.", parent=dialogo
            )
            return
        if peso <= 0:
            messagebox.showwarning(
                "1RM", "El peso debe ser mayor a 0.", parent=dialogo
            )
            return
        rpe = reps = None
        try:
            if rama == "rpe":
                rpe = int(combo_rpe.get())
                uno_rm = uno_rm_por_rpe(peso, rpe)
                metodo = "RPE (Fashi et al., 2024)"
            else:
                reps = int(entrada_reps.get())
                uno_rm = uno_rm_por_repeticiones(peso, reps)
                metodo = "Repeticiones (Brzycki)"
        except ValueError as error:
            messagebox.showwarning("1RM", str(error), parent=dialogo)
            return

        resultado_ultimo["datos"] = {
            "ejercicio": "Press de banca",
            "metodo": metodo,
            "peso": peso,
            "rpe": rpe,
            "repeticiones": reps,
            "resultado": round(uno_rm, 1),
        }

        lbl_1rm.configure(text=f"1RM ESTIMADO: {uno_rm:.1f} kg")
        for item in tabla.get_children():
            tabla.delete(item)
        for pct in PORCENTAJES:
            kg = uno_rm * pct / 100.0
            fuerte = "fuerte" if pct in (80, 85, 90) else ""
            tabla.insert(
                "", "end",
                values=(f"{pct}%", f"{kg:.1f} kg",
                        f"{_redondear_discos(kg):g} kg"),
                tags=(fuerte,),
            )

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
        messagebox.showinfo(
            "1RM",
            f"1RM de press de banca ({datos['resultado']} kg, "
            f"método {datos['metodo']}) guardado para el paciente activo.",
            parent=dialogo,
        )

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
            lbl_1rm.configure(text="1RM ESTIMADO: —"),
            resultado_ultimo.update({"datos": None}),
            *[tabla.delete(i) for i in tabla.get_children()],
        ),
        font=("Impact", 13), fg=NEON, bg=GRIS,
        activebackground=NARANJA, activeforeground=BLANCO,
        relief="flat", padx=16, pady=6, cursor="hand2",
    ).pack(side="left")

    arbol.bind("<<TreeviewSelect>>", lambda _e: _mostrar_formulario())

    # rama inicial
    arbol.selection_set("rpe")
    _mostrar_formulario()

    dialogo.update_idletasks()
    x = max(0, (dialogo.winfo_screenwidth() - dialogo.winfo_width()) // 2)
    y = max(0, (dialogo.winfo_screenheight() - dialogo.winfo_height()) // 2)
    dialogo.geometry(f"+{x}+{y}")
    dialogo.wait_window(dialogo)
