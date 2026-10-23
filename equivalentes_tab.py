"""
Pestaña Equivalentes - Cuadro dietosintético y distribución de equivalentes.
Toma la energía calculada en Fórmulas predictivas (TEE), reparte el 100%
entre Carbohidratos, Proteína y Grasa y calcula equivalentes por subgrupo
(SMAE-5).
"""
import json
import tkinter as tk
from tkinter import messagebox, ttk

import database
import equivalentes_print

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"

# Tabla de aporte nutrimental promedio por subgrupo SMAE-5
# (grupo, kcal, proteína g, lípidos g, HC g)
EQUIVALENTES_DATA = [
    ("Verduras", "-", 25, 2, 0, 4),
    ("Frutas", "-", 60, 0, 0, 15),
    ("Cereales sin grasa", "-", 70, 2, 0, 15),
    ("Cereales con grasa", "-", 115, 2, 5, 15),
    ("Leguminosas", "-", 120, 8, 1, 20),
    ("AOA", "Muy bajo aporte de grasa", 40, 7, 1, 0),
    ("AOA", "Bajo aporte de grasa", 55, 7, 3, 0),
    ("AOA", "Moderado aporte de grasa", 75, 7, 5, 0),
    ("AOA", "Alto aporte de grasa", 100, 7, 8, 0),
    ("Leche", "Descremada", 95, 9, 2, 12),
    ("Leche", "Semidescremada", 110, 9, 4, 12),
    ("Leche", "Entera", 150, 9, 8, 12),
    ("Leche", "Con azúcar", 200, 8, 5, 30),
    ("Aceites y grasas", "Sin proteína", 45, 0, 5, 0),
    ("Aceites y grasas", "Con proteína", 70, 3, 5, 3),
    ("Azúcares", "Sin grasa", 40, 0, 0, 10),
    ("Azúcares", "Con grasa", 85, 0, 5, 10),
]

# Días de la semana para distribuir equivalentes día por día
DIAS_SEMANA = [
    "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo",
]

# Nombres por defecto de los tiempos de comida según el número de tiempos
TIEMPOS_PREDEF = {
    3: ["Desayuno", "Comida", "Cena"],
    4: ["Desayuno", "Colación Matutina", "Comida", "Cena"],
    5: ["Desayuno", "Colación Matutina", "Comida", "Colación Vespertina", "Cena"],
    6: [
        "Desayuno", "Colación Matutina", "Comida",
        "Colación Vespertina", "Cena", "Colación Nocturna",
    ],
}


class EquivalesTab:
    def __init__(self, app):
        self.app = app

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  🥗 Equivalentes  ")
        self.marco_canvas = self.marco

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
            text="CUADRO DIETOSINTÉTICO Y EQUIVALENTES",
            font=("Impact", 20),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 6))

        # ----- Energía / peso -----
        info = ttk.LabelFrame(self.marco, text="Energía", padding=8)
        info.pack(fill="x", padx=8, pady=4)

        ttk.Label(info, text="TEE (kcal):", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=4
        )
        self.tee_var = tk.StringVar(value="")
        self.tee_var.trace_add("write", self.recalcular)
        ttk.Entry(info, textvariable=self.tee_var, width=10,
                  style="Gym.TEntry").pack(side=tk.LEFT, padx=4)

        ttk.Label(info, text="Peso (kg):", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(16, 4)
        )
        self.peso_var = tk.StringVar(value="")
        self.peso_var.trace_add("write", self.recalcular)
        ttk.Entry(info, textvariable=self.peso_var, width=10,
                  style="Gym.TEntry").pack(side=tk.LEFT, padx=4)

        tk.Button(
            info,
            text="TOMAR DE FÓRMULAS",
            command=self.tomar_de_formulas,
            font=("Impact", 10),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=10)

        # ----- Cuadro dietosintético -----
        cuadro = ttk.LabelFrame(
            self.marco, text="Cuadro dietosintético", padding=8
        )
        cuadro.pack(fill="x", padx=8, pady=4)

        encabezados = ["Macronutriente", "%", "kcal", "Gramos", "g/kg peso"]
        for c, texto in enumerate(encabezados):
            ttk.Label(cuadro, text=texto, style="Estado.TLabel").grid(
                row=0, column=c, padx=12, pady=4
            )

        self.pct_carb = tk.StringVar(value="55")
        self.pct_prot = tk.StringVar(value="15")
        self.pct_grasa = tk.StringVar(value="30")
        for var in (self.pct_carb, self.pct_prot, self.pct_grasa):
            var.trace_add("write", self.recalcular)

        self.lbl_kcal = {}
        self.lbl_g = {}
        self.lbl_gkg = {}
        filas = [
            ("carbohidratos", "Carbohidratos", self.pct_carb),
            ("proteina", "Proteína", self.pct_prot),
            ("grasa", "Grasa", self.pct_grasa),
        ]
        for i, (clave, etiqueta, var) in enumerate(filas, start=1):
            ttk.Label(cuadro, text=etiqueta, style="Gym.TLabel").grid(
                row=i, column=0, sticky="w", padx=8, pady=3
            )
            ttk.Entry(cuadro, textvariable=var, width=6, justify="center",
                      style="Gym.TEntry").grid(
                row=i, column=1, padx=8, pady=3
            )
            self.lbl_kcal[clave] = tk.Label(cuadro, text="0", fg=NEON,
                                            bg=GRIS_OSCURO, width=10)
            self.lbl_kcal[clave].grid(row=i, column=2, padx=8, pady=3)
            self.lbl_g[clave] = tk.Label(cuadro, text="0", fg=BLANCO,
                                         bg=GRIS_OSCURO, width=10)
            self.lbl_g[clave].grid(row=i, column=3, padx=8, pady=3)
            self.lbl_gkg[clave] = tk.Label(cuadro, text="0", fg=BLANCO,
                                           bg=GRIS_OSCURO, width=10)
            self.lbl_gkg[clave].grid(row=i, column=4, padx=8, pady=3)

        ttk.Label(cuadro, text="TOTAL", style="Estado.TLabel").grid(
            row=4, column=0, sticky="w", padx=8, pady=3
        )
        self.lbl_total_pct = tk.Label(cuadro, text="100%", fg=NEON,
                                      bg=GRIS_OSCURO, width=6)
        self.lbl_total_pct.grid(row=4, column=1, padx=8, pady=3)
        self.lbl_total_kcal = tk.Label(cuadro, text="0", fg=NEON,
                                       bg=GRIS_OSCURO, width=10)
        self.lbl_total_kcal.grid(row=4, column=2, padx=8, pady=3)
        self.lbl_total_g = tk.Label(cuadro, text="0", fg=NEON,
                                    bg=GRIS_OSCURO, width=10)
        self.lbl_total_g.grid(row=4, column=3, padx=8, pady=3)

        # ----- Equivalentes por subgrupo -----
        eq_frame = ttk.LabelFrame(
            self.marco, text="Distribución de equivalentes (SMAE-5)", padding=6
        )
        eq_frame.pack(fill="both", expand=True, padx=8, pady=4)

        columnas = (
            "grupo", "subgrupo", "kcal", "prot", "lip", "hc",
            "eq_calc", "eq",
            "kcal_t", "prot_t", "lip_t", "hc_t",
        )
        self.eq_tree = ttk.Treeview(
            eq_frame, columns=columnas, show="headings", height=19,
            style="Eq.Treeview",
        )
        for col, texto, ancho in (
            ("grupo", "Grupo", 130),
            ("subgrupo", "Subgrupo", 150),
            ("kcal", "kcal", 50),
            ("prot", "Prot", 45),
            ("lip", "Lip", 45),
            ("hc", "HC", 45),
            ("eq_calc", "Calc.", 55),
            ("eq", "Eq.", 90),
            ("kcal_t", "kcal T", 60),
            ("prot_t", "Prot T", 55),
            ("lip_t", "Lip T", 50),
            ("hc_t", "HC T", 50),
        ):
            self.eq_tree.heading(col, text=texto)
            self.eq_tree.column(col, width=ancho, anchor="center")
        self.eq_tree.column("grupo", anchor="w")
        self.eq_tree.column("subgrupo", anchor="w")
        self.eq_tree.pack(fill="both", expand=True)

        self.eq_tree.bind("<Configure>", lambda _e: self._posicionar_inputs())
        self.eq_tree.bind("<MouseWheel>", lambda _e: self._reposicionar_after())

        self.inputs_eq = []

        barra = ttk.Frame(eq_frame, style="Gym.TFrame")
        barra.pack(fill="x", pady=4)
        tk.Button(
            barra, text="SUGERIR EQUIVALENTES", command=self.sugerir_equivalentes,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            barra, text="LIMPIAR", command=self.limpiar_equivalentes,
            font=("Impact", 10), fg=NEON, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            barra, text="GUARDAR", command=self.guardar,
            font=("Impact", 10), fg=NEGRO, bg=NARANJA, activebackground=NEON,
            activeforeground=NEGRO, relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            barra, text="IMPRIMIR", command=self.imprimir,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)

        self.equivalentes = [tk.StringVar(value="0") for _ in EQUIVALENTES_DATA]
        for var in self.equivalentes:
            var.trace_add("write", self._actualizar_totales)

        self._construir_tabla_equivalentes()
        self._actualizar_totales()

        # ----- Distribución por tiempos de comida -----
        dist_frame = ttk.LabelFrame(
            self.marco, text="Distribución por tiempos", padding=6
        )
        dist_frame.pack(fill="x", padx=8, pady=4)

        # Selector de día de la semana
        dias_bar = ttk.Frame(dist_frame, style="Gym.TFrame")
        dias_bar.pack(fill="x", pady=(0, 4))
        ttk.Label(dias_bar, text="Día:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        self.dia_actual = DIAS_SEMANA[0]
        self.dia_buttons = {}
        for dia in DIAS_SEMANA:
            btn = tk.Button(
                dias_bar, text=dia, command=lambda d=dia: self._cambiar_dia(d),
                font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
                activebackground=NARANJA, activeforeground=BLANCO,
                relief="flat", padx=8, pady=3, cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.dia_buttons[dia] = btn

        controles = ttk.Frame(dist_frame, style="Gym.TFrame")
        controles.pack(fill="x", pady=(0, 6))

        ttk.Label(controles, text="Número de tiempos:",
                  style="Gym.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self.num_tiempos_var = tk.StringVar(value="4")
        combo = ttk.Combobox(
            controles, textvariable=self.num_tiempos_var, width=4,
            values=("3", "4", "5", "6"), state="readonly",
            style="Gym.TCombobox",
        )
        combo.pack(side=tk.LEFT, padx=4)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _e: self.reconstruir_tabla_distribucion(),
        )

        tk.Button(
            controles, text="RECONSTRUIR", command=self.reconstruir_tabla_distribucion,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            controles, text="DISTRIBUIR", command=self.distribuir_automatico,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            controles, text="LIMPIAR", command=self.limpiar_distribucion,
            font=("Impact", 10), fg=NEON, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)

        self.dist_frame = ttk.Frame(dist_frame, style="Gym.TFrame")
        self.dist_frame.pack(fill="x")

        self.dist_datos = {}
        self._registrar_dia_actual()
        self.reconstruir_tabla_distribucion()
        self._resaltar_dia()

    # ------------------------------------------------------------------
    def _construir_tabla_equivalentes(self):
        for item in self.eq_tree.get_children():
            self.eq_tree.delete(item)
        for widget in getattr(self, "inputs_eq", []):
            widget.destroy()
        self.inputs_eq = []
        for i, (grupo, subgrupo, kcal, prot, lip, hc) in enumerate(
            EQUIVALENTES_DATA
        ):
            self.eq_tree.insert(
                "", tk.END, iid=str(i),
                values=(
                    grupo, subgrupo, kcal, prot, lip, hc,
                    "0", "0", "0", "0", "0", "0",
                ),
            )
            entrada = ttk.Entry(
                self.eq_tree, textvariable=self.equivalentes[i],
                justify="center", style="Gym.TEntry",
            )
            self.inputs_eq.append(entrada)
        self.eq_tree.insert(
            "", tk.END, iid="total",
            values=("TOTAL", "", "", "", "", "", "", "", "0", "0", "0", "0"),
            tags=("total",),
        )
        self.eq_tree.tag_configure(
            "total", background=GRIS, foreground=NEON,
            font=("Segoe UI", 10, "bold"),
        )
        self.eq_tree.after(50, self._posicionar_inputs)

    def _posicionar_inputs(self):
        if not getattr(self, "inputs_eq", None):
            return
        for i, entrada in enumerate(self.inputs_eq):
            bbox = self.eq_tree.bbox(str(i), "#8")
            if not bbox:
                entrada.place_forget()
                continue
            x, y, ancho, alto = bbox
            alto_entry = max(alto - 2, 22)
            entrada.place(
                x=x + 2, y=y + 1, width=max(ancho - 4, 40), height=alto_entry
            )

    def _reposicionar_after(self):
        self.eq_tree.after_idle(self._posicionar_inputs)

    def _actualizar_totales(self, *args):
        totales = {"kcal": 0.0, "prot": 0.0, "lip": 0.0, "hc": 0.0}
        self.total_eq = 0.0
        self.total_eq_calc = 0.0
        objetivo = self._objetivo_equivalentes()
        for i, (grupo, subgrupo, kcal, prot, lip, hc) in enumerate(
            EQUIVALENTES_DATA
        ):
            try:
                eq = float(self.equivalentes[i].get() or 0)
            except ValueError:
                eq = 0.0
            calc = objetivo[i] if i < len(objetivo) else 0
            self.total_eq += eq
            self.total_eq_calc += calc
            fila_totales = [kcal * eq, prot * eq, lip * eq, hc * eq]
            for clave, valor in zip(("kcal", "prot", "lip", "hc"), fila_totales):
                totales[clave] += valor
            self.eq_tree.item(
                str(i),
                values=(
                    grupo, subgrupo, kcal, prot, lip, hc,
                    f"{calc:g}",
                    f"{eq:g}",
                    *[f"{v:.1f}" for v in fila_totales],
                ),
            )
        self.totales_eq = totales
        self._actualizar_totales_eq()
        self._actualizar_faltantes()
        self.actualizar_objetivos_distribucion()

    def _actualizar_totales_eq(self):
        self.eq_tree.item(
            "total",
            values=(
                "TOTAL DEL DÍA", "", "", "", "", "", "", "",
                f"{self.totales_eq['kcal']:.1f}",
                f"{self.totales_eq['prot']:.1f}",
                f"{self.totales_eq['lip']:.1f}",
                f"{self.totales_eq['hc']:.1f}",
            ),
        )

    def _actualizar_faltantes(self):
        if not hasattr(self, "faltante_labels"):
            return
        objetivo_eq = self._objetivo_equivalentes()
        for i, etiqueta in enumerate(self.faltante_labels):
            antes = objetivo_eq[i] if i < len(objetivo_eq) else 0
            try:
                actual = float(self.equivalentes[i].get() or 0)
            except ValueError:
                actual = 0.0
            falta = antes - actual
            etiqueta.configure(
                text=f"{falta:.1f}",
                fg=NEON if abs(falta) < 0.05 else NARANJA,
            )

    def _objetivo_equivalentes(self):
        gramos = getattr(self, "gramos", None)
        if not gramos:
            return [0] * len(EQUIVALENTES_DATA)
        carb = gramos["carbohidratos"]
        prot = gramos["proteina"]
        grasa = gramos["grasa"]
        return [
            5,                                  # Verduras
            max(0, round(carb * 0.15 / 15)),    # Frutas
            max(0, round(carb * 0.50 / 15)),    # Cereales sin grasa
            max(0, round(carb * 0.10 / 15)),    # Cereales con grasa
            max(0, round(carb * 0.08 / 20)),    # Leguminosas
            max(0, round(prot * 0.35 / 7)),     # AOA MBAG
            max(0, round(prot * 0.25 / 7)),     # AOA BAG
            max(0, round(prot * 0.20 / 7)),     # AOA MAG
            max(0, round(prot * 0.10 / 7)),     # AOA AAG
            max(0, round(prot * 0.10 / 9)),     # Leche descremada
            0,                                  # Leche semidescremada
            0,                                  # Leche entera
            0,                                  # Leche con azúcar
            max(0, round(grasa * 0.80 / 5)),    # Aceites y grasas
            0,                                  # Aceites y grasas con proteína
            0,                                  # Azúcares sin grasa
            0,                                  # Azúcares con grasa
        ]

    # ------------------------------------------------------------------
    # Distribución por tiempos de comida (por día de la semana)
    # ------------------------------------------------------------------
    def _registrar_dia_actual(self):
        """Guarda el estado visible (tiempos, nombres y equivalentes) del día."""
        if not getattr(self, "dist_vars", None):
            return
        valores = [
            [var.get() for var in fila_vars] for fila_vars in self.dist_vars
        ]
        nombres = [v.get() for v in getattr(self, "dist_nombres_vars", [])]
        self.dist_datos[self.dia_actual] = {
            "num_t": int(self.num_tiempos_var.get()),
            "nombres": nombres,
            "valores": valores,
        }

    def _cambiar_dia(self, dia):
        if dia == self.dia_actual:
            return
        self._registrar_dia_actual()
        self.dia_actual = dia
        self._resaltar_dia()
        self._cargar_dia(dia)

    def _cargar_dia(self, dia):
        datos = self.dist_datos.get(dia)
        if datos:
            self.num_tiempos_var.set(str(datos["num_t"]))
        self._cargando_dia = True
        try:
            self.reconstruir_tabla_distribucion()
        finally:
            self._cargando_dia = False

    def _resaltar_dia(self):
        for dia, btn in getattr(self, "dia_buttons", {}).items():
            seleccionado = dia == self.dia_actual
            btn.configure(
                bg=NEON if seleccionado else GRIS,
                fg=NEGRO if seleccionado else BLANCO,
            )

    def reconstruir_tabla_distribucion(self):
        if not getattr(self, "_cargando_dia", False):
            self._registrar_dia_actual()
        for widget in self.dist_frame.winfo_children():
            widget.destroy()

        try:
            num_t = int(self.num_tiempos_var.get())
        except ValueError:
            num_t = 4
        datos = self.dist_datos.get(self.dia_actual) or {}
        nombres_guardados = datos.get("nombres") or []
        valores_guardados = datos.get("valores") or []
        nombres_defecto = TIEMPOS_PREDEF.get(
            num_t, [f"Tiempo {i + 1}" for i in range(num_t)]
        )

        self.dist_frame.grid_columnconfigure(0, weight=2)
        for t_idx in range(num_t):
            self.dist_frame.grid_columnconfigure(t_idx + 1, weight=1)
        for c in (num_t + 1, num_t + 2, num_t + 3):
            self.dist_frame.grid_columnconfigure(c, weight=1)

        ttk.Label(self.dist_frame, text="Subgrupo", style="Estado.TLabel").grid(
            row=0, column=0, sticky="nsew", padx=1, pady=1
        )
        self.dist_nombres_vars = []
        for t_idx in range(num_t):
            if t_idx < len(nombres_guardados):
                inicial = nombres_guardados[t_idx]
            else:
                inicial = nombres_defecto[t_idx]
            nombre_var = tk.StringVar(value=inicial)
            ttk.Entry(
                self.dist_frame, textvariable=nombre_var, justify="center",
                style="Gym.TEntry",
            ).grid(row=0, column=t_idx + 1, sticky="nsew", padx=1, pady=1)
            self.dist_nombres_vars.append(nombre_var)

        for offset, texto in enumerate(("Total", "Objetivo", "Falta")):
            ttk.Label(self.dist_frame, text=texto, style="Estado.TLabel").grid(
                row=0, column=num_t + 1 + offset, sticky="nsew", padx=1, pady=1
            )

        self.dist_vars = []
        self.dist_totales_labels = []
        self.dist_objetivo_labels = []
        self.dist_diferencia_labels = []

        for sg_idx, (grupo, subgrupo, *_resto) in enumerate(EQUIVALENTES_DATA):
            row_idx = sg_idx + 1
            texto_grupo = grupo if subgrupo == "-" else f"{grupo} ({subgrupo})"
            tk.Label(
                self.dist_frame, text=texto_grupo, anchor="w", font=("Segoe UI", 8),
                fg=BLANCO, bg=GRIS_OSCURO,
            ).grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)

            fila_vars = []
            fila_guardada = (
                valores_guardados[sg_idx] if sg_idx < len(valores_guardados) else []
            )
            for t_idx in range(num_t):
                inicial = (
                    fila_guardada[t_idx] if t_idx < len(fila_guardada) else "0"
                )
                var = tk.StringVar(value=inicial)
                var.trace_add("write", self.calcular_distribucion_manual)
                ttk.Entry(
                    self.dist_frame, textvariable=var, width=4, justify="center",
                    style="Gym.TEntry",
                ).grid(row=row_idx, column=t_idx + 1, sticky="nsew", padx=1, pady=1)
                fila_vars.append(var)
            self.dist_vars.append(fila_vars)

            lbl_total = tk.Label(self.dist_frame, text="0", fg=BLANCO,
                                 bg=GRIS_OSCURO, font=("Segoe UI", 9))
            lbl_total.grid(row=row_idx, column=num_t + 1, sticky="nsew",
                           padx=1, pady=1)
            self.dist_totales_labels.append(lbl_total)

            lbl_obj = tk.Label(self.dist_frame, text="0", fg=BLANCO,
                               bg=GRIS_OSCURO, font=("Segoe UI", 9))
            lbl_obj.grid(row=row_idx, column=num_t + 2, sticky="nsew",
                         padx=1, pady=1)
            self.dist_objetivo_labels.append(lbl_obj)

            lbl_diff = tk.Label(self.dist_frame, text="0", fg=NARANJA,
                                bg=GRIS_OSCURO, font=("Segoe UI", 9))
            lbl_diff.grid(row=row_idx, column=num_t + 3, sticky="nsew",
                          padx=1, pady=1)
            self.dist_diferencia_labels.append(lbl_diff)

        total_row = len(EQUIVALENTES_DATA) + 1
        ttk.Label(self.dist_frame, text="kcal", style="Estado.TLabel").grid(
            row=total_row, column=0, sticky="nsew", padx=1, pady=1
        )
        self.dist_kcal_labels = []
        for t_idx in range(num_t):
            lbl_k = tk.Label(self.dist_frame, text="0", fg=NEON, bg=GRIS_OSCURO,
                             font=("Segoe UI", 9), width=8)
            lbl_k.grid(row=total_row, column=t_idx + 1, sticky="nsew",
                       padx=1, pady=1)
            self.dist_kcal_labels.append(lbl_k)
        self.lbl_dist_total_kcal = tk.Label(
            self.dist_frame, text="0", fg=NEON, bg=GRIS_OSCURO,
            font=("Segoe UI", 9, "bold"), width=8,
        )
        self.lbl_dist_total_kcal.grid(row=total_row, column=num_t + 1,
                                      sticky="nsew", padx=1, pady=1)

        self.actualizar_objetivos_distribucion()

    def actualizar_objetivos_distribucion(self):
        if not getattr(self, "dist_objetivo_labels", None):
            return
        for j, var in enumerate(self.equivalentes):
            try:
                val = float(var.get() or 0)
            except ValueError:
                val = 0.0
            self.dist_objetivo_labels[j].configure(text=f"{val:.0f}")
        self.calcular_distribucion_manual()

    def calcular_distribucion_manual(self, *args):
        if not getattr(self, "dist_vars", None) or not self.dist_vars:
            return
        num_t = len(self.dist_vars[0])
        time_kcals = [0.0] * num_t
        total_general_kcal = 0.0

        for sg_idx, fila_vars in enumerate(self.dist_vars):
            sg_total = 0.0
            kcal_val_sg = EQUIVALENTES_DATA[sg_idx][2]
            for t_idx, var in enumerate(fila_vars):
                try:
                    eq = float(var.get() or 0)
                except ValueError:
                    eq = 0.0
                sg_total += eq
                time_kcals[t_idx] += kcal_val_sg * eq

            self.dist_totales_labels[sg_idx].configure(text=f"{sg_total:.0f}")

            try:
                obj_val = float(self.dist_objetivo_labels[sg_idx].cget("text") or 0)
            except ValueError:
                obj_val = 0.0
            diff = obj_val - sg_total
            self.dist_diferencia_labels[sg_idx].configure(
                text=f"{diff:.0f}", fg=NEON if abs(diff) < 0.05 else NARANJA
            )
            total_general_kcal += kcal_val_sg * sg_total

        for t_idx, k in enumerate(time_kcals):
            self.dist_kcal_labels[t_idx].configure(text=f"{k:.1f}")
        self.lbl_dist_total_kcal.configure(text=f"{total_general_kcal:.1f}")

    def distribuir_automatico(self):
        try:
            num_t = int(self.num_tiempos_var.get())
        except ValueError:
            num_t = 4
        pcts_por_num = {
            3: [0.30, 0.35, 0.35],
            4: [0.25, 0.15, 0.30, 0.30],
            5: [0.25, 0.10, 0.30, 0.10, 0.25],
            6: [0.20, 0.10, 0.30, 0.10, 0.20, 0.10],
        }
        pcts = pcts_por_num.get(num_t, [1 / num_t] * num_t)

        eq_totales = []
        for var in self.equivalentes:
            try:
                eq_totales.append(float(var.get() or 0))
            except ValueError:
                eq_totales.append(0.0)

        for sg_idx, fila_vars in enumerate(self.dist_vars):
            for t_idx, var in enumerate(fila_vars):
                var.set(str(round(eq_totales[sg_idx] * pcts[t_idx])))
        self._registrar_dia_actual()

    def limpiar_distribucion(self):
        for fila_vars in getattr(self, "dist_vars", []):
            for var in fila_vars:
                var.set("0")
        self._registrar_dia_actual()

    def distribuciones_dato(self):
        """Devuelve el diccionario de los 7 días para persistir."""
        self._registrar_dia_actual()
        return {
            dia: self.dist_datos.get(dia, {"num_t": 4, "nombres": [], "valores": []})
            for dia in DIAS_SEMANA
        }

    def cargar_distribuciones(self, datos):
        """Restaura los 7 días desde un diccionario persistido."""
        if not datos:
            return
        for dia in DIAS_SEMANA:
            info = datos.get(dia)
            if not info:
                continue
            self.dist_datos[dia] = {
                "num_t": int(info.get("num_t", 4)),
                "nombres": info.get("nombres", []),
                "valores": info.get("valores", []),
            }
        self._cargar_dia(self.dia_actual)

    def sugerir_equivalentes(self):
        objetivo = self._objetivo_equivalentes()
        for i, valor in enumerate(objetivo):
            self.equivalentes[i].set(str(valor))
        self._actualizar_totales()

    def limpiar_equivalentes(self):
        for var in self.equivalentes:
            var.set("0")

    def limpiar(self):
        """Resetea el plan de equivalentes y las distribuciones por día."""
        for var in self.equivalentes:
            var.set("0")
        for fila_vars in getattr(self, "dist_vars", []):
            for var in fila_vars:
                var.set("0")
        self.dist_datos = {}
        for var in getattr(self, "dist_nombres_vars", []):
            var.set("")
        self._actualizar_totales()

    def guardar(self):
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            messagebox.showwarning(
                "Equivalentes",
                "Selecciona un paciente antes de guardar.",
            )
            return
        try:
            tee = float(self.tee_var.get().replace(",", "."))
        except ValueError:
            tee = 0.0
        try:
            peso = float(self.peso_var.get().replace(",", "."))
        except ValueError:
            peso = 0.0

        detalle = [
            {
                "grupo": grupo,
                "subgrupo": subgrupo,
                "equivalentes": float(self.equivalentes[i].get() or 0),
            }
            for i, (grupo, subgrupo, _k, _p, _l, _h) in enumerate(
                EQUIVALENTES_DATA
            )
        ]
        datos = {
            "paciente_id": paciente_id,
            "tee": tee,
            "peso": peso,
            "pct_carb": float(self.pct_carb.get().replace(",", ".") or 0),
            "pct_prot": float(self.pct_prot.get().replace(",", ".") or 0),
            "pct_grasa": float(self.pct_grasa.get().replace(",", ".") or 0),
            "total_kcal": self.totales_eq["kcal"],
            "total_prot": self.totales_eq["prot"],
            "total_lip": self.totales_eq["lip"],
            "total_hc": self.totales_eq["hc"],
            "detalle": json.dumps(
                {
                    "equivalentes": detalle,
                    "dias": self.distribuciones_dato(),
                },
                ensure_ascii=False,
            ),
        }
        database.insert_equivalentes(datos)
        messagebox.showinfo(
            "Equivalentes",
            "Distribución de equivalentes guardada para el paciente activo.",
        )

    def imprimir(self):
        """Genera el PDF del plan de equivalentes y lo abre en Acrobat."""
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            messagebox.showwarning(
                "Equivalentes",
                "Selecciona un paciente antes de imprimir.",
            )
            return

        def num(var):
            try:
                return float(var.get().replace(",", "."))
            except (AttributeError, ValueError):
                return 0.0

        self._registrar_dia_actual()
        filas_equivalentes = []
        for i, (grupo, subgrupo, kcal, prot, lip, hc) in enumerate(
            EQUIVALENTES_DATA
        ):
            try:
                eq = float(self.equivalentes[i].get() or 0)
            except ValueError:
                eq = 0.0
            filas_equivalentes.append((grupo, subgrupo, kcal, prot, lip, hc, eq))

        dias = {}
        for dia in DIAS_SEMANA:
            info = self.dist_datos.get(dia) or {}
            dias[dia] = {
                "nombres": info.get("nombres") or [],
                "valores": info.get("valores") or [],
            }

        plan = {
            "tee": num(self.tee_var),
            "peso": num(self.peso_var),
            "pct_carb": num(self.pct_carb),
            "pct_prot": num(self.pct_prot),
            "pct_grasa": num(self.pct_grasa),
            "gramos": getattr(self, "gramos", None) or {},
            "totales": getattr(self, "totales_eq", None) or {},
            "filas_equivalentes": filas_equivalentes,
            "dias": dias,
        }

        paciente = database.obtener_paciente(paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{paciente_id}"
        ruta = equivalentes_print.ruta_temporal_pdf(nombre)
        try:
            equivalentes_print.generar_pdf_equivalentes(ruta, paciente, plan)
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            equivalentes_print.abrir_para_imprimir(ruta)
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
            "Incluye membrete, datos del paciente y fecha de impresión.",
        )

    def cargar(self, paciente_id):
        """Carga el último plan de equivalentes (incluidas distribuciones)."""
        registros = database.get_equivalentes(paciente_id)
        if not registros:
            self.limpiar()
            return
        registro = registros[0]
        try:
            info = json.loads(registro.get("detalle") or "{}")
        except (json.JSONDecodeError, TypeError):
            info = {}
        equivalentes = info.get("equivalentes")
        if isinstance(equivalentes, list):
            for i, item in enumerate(equivalentes):
                if i < len(self.equivalentes):
                    self.equivalentes[i].set(str(item.get("equivalentes", 0)))
        dias = info.get("dias")
        if dias:
            self.cargar_distribuciones(dias)

    # ------------------------------------------------------------------
    def tomar_de_formulas(self, silencioso=False):
        tab = getattr(self.app, "tab_formulas", None)
        if tab is None or tab.tee is None:
            if not silencioso:
                messagebox.showinfo(
                    "Fórmulas predictivas",
                    "Primero calcula el TEE en la pestaña Fórmulas predictivas.",
                )
            return
        self.tee_var.set(f"{tab.tee:.1f}")
        if tab.peso:
            self.peso_var.set(f"{tab.peso:.1f}")

    def recalcular(self, *args):
        try:
            tee = float(self.tee_var.get().replace(",", "."))
        except ValueError:
            tee = 0.0
        try:
            peso = float(self.peso_var.get().replace(",", "."))
        except ValueError:
            peso = 0.0

        def pct(var):
            try:
                return float(var.get().replace(",", "."))
            except ValueError:
                return 0.0

        p_carb, p_prot, p_grasa = (
            pct(self.pct_carb), pct(self.pct_prot), pct(self.pct_grasa)
        )
        total_pct = p_carb + p_prot + p_grasa
        self.lbl_total_pct.configure(
            text=f"{total_pct:.0f}%",
            fg=NEON if abs(total_pct - 100) < 0.01 else NARANJA,
        )

        kcal_carb = tee * p_carb / 100
        kcal_prot = tee * p_prot / 100
        kcal_grasa = tee * p_grasa / 100

        g_carb = kcal_carb / 4
        g_prot = kcal_prot / 4
        g_grasa = kcal_grasa / 9

        self.gramos = {
            "carbohidratos": g_carb,
            "proteina": g_prot,
            "grasa": g_grasa,
        }
        for clave, kcal, gramos in (
            ("carbohidratos", kcal_carb, g_carb),
            ("proteina", kcal_prot, g_prot),
            ("grasa", kcal_grasa, g_grasa),
        ):
            self.lbl_kcal[clave].configure(text=f"{kcal:.1f}")
            self.lbl_g[clave].configure(text=f"{gramos:.1f}")
            self.lbl_gkg[clave].configure(
                text=f"{gramos / peso:.2f}" if peso else "0"
            )

        self.lbl_total_kcal.configure(text=f"{tee:.1f}")
        self.lbl_total_g.configure(text=f"{g_carb + g_prot + g_grasa:.1f}")

        self._actualizar_faltantes()

