"""
Pestaña Equivalentes - Cuadro dietosintético y distribución por tiempos.
Toma la energía calculada en Fórmulas predictivas (TEE), reparte el 100%
entre Carbohidratos, Proteína y Grasa, calcula equivalentes por subgrupo
(SMAE-5) y los distribuye en los tiempos de comida (basado en HCEmbarazo).
"""
import tkinter as tk
from tkinter import messagebox, ttk

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

TIEMPOS_PREDEF = {
    3: ["Desayuno", "Comida", "Cena"],
    4: ["Desayuno", "Colación matutina", "Comida", "Cena"],
    5: ["Desayuno", "Colación matutina", "Comida", "Colación vespertina", "Cena"],
    6: [
        "Desayuno", "Colación matutina", "Comida",
        "Colación vespertina", "Cena", "Colación nocturna",
    ],
}


class EquivalesTab:
    def __init__(self, app):
        self.app = app

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  🥗 Equivalentes  ")

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
        ttk.Entry(info, textvariable=self.tee_var, width=10).pack(
            side=tk.LEFT, padx=4
        )

        ttk.Label(info, text="Peso (kg):", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(16, 4)
        )
        self.peso_var = tk.StringVar(value="")
        self.peso_var.trace_add("write", self.recalcular)
        ttk.Entry(info, textvariable=self.peso_var, width=10).pack(
            side=tk.LEFT, padx=4
        )

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
            ttk.Entry(cuadro, textvariable=var, width=6, justify="center").grid(
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
            "grupo", "subgrupo", "kcal", "prot", "lip", "hc", "eq",
            "kcal_t", "prot_t", "lip_t", "hc_t",
        )
        self.eq_tree = ttk.Treeview(
            eq_frame, columns=columnas, show="headings", height=17,
            style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("grupo", "Grupo", 130),
            ("subgrupo", "Subgrupo", 150),
            ("kcal", "kcal", 50),
            ("prot", "Prot", 45),
            ("lip", "Lip", 45),
            ("hc", "HC", 45),
            ("eq", "Eq.", 55),
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

        self.eq_tree.bind("<Double-1>", self._editar_eq)

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

        # ----- Distribución por tiempos -----
        dist_frame = ttk.LabelFrame(
            self.marco, text="Distribución por tiempos de comida", padding=6
        )
        dist_frame.pack(fill="x", padx=8, pady=(0, 6))

        ctrl = ttk.Frame(dist_frame, style="Gym.TFrame")
        ctrl.pack(fill="x", pady=2)
        ttk.Label(ctrl, text="Número de tiempos:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=4
        )
        self.num_var = tk.StringVar(value="4")
        combo = ttk.Combobox(
            ctrl, textvariable=self.num_var, values=["3", "4", "5", "6"],
            width=5, state="readonly",
        )
        combo.pack(side=tk.LEFT, padx=4)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.reconstruir_tiempos())

        self.dist_contenedor = ttk.Frame(dist_frame, style="Gym.TFrame")
        self.dist_contenedor.pack(fill="x", pady=4)

        self.equivalentes = [tk.StringVar(value="0") for _ in EQUIVALENTES_DATA]
        for var in self.equivalentes:
            var.trace_add("write", self._actualizar_totales)

        self._construir_tabla_equivalentes()
        self.reconstruir_tiempos()

    # ------------------------------------------------------------------
    def _construir_tabla_equivalentes(self):
        for item in self.eq_tree.get_children():
            self.eq_tree.delete(item)
        for i, (grupo, subgrupo, kcal, prot, lip, hc) in enumerate(
            EQUIVALENTES_DATA
        ):
            self.eq_tree.insert(
                "", tk.END, iid=str(i),
                values=(grupo, subgrupo, kcal, prot, lip, hc, "0", "0", "0", "0", "0"),
            )

    def _editar_eq(self, event=None):
        sel = self.eq_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        grupo, subgrupo, kcal, prot, lip, hc = EQUIVALENTES_DATA[idx]
        actual = self.equivalentes[idx].get()
        valor = _pedir_valor(
            self.marco, f"Equivalentes de {grupo} ({subgrupo})", actual
        )
        if valor is None:
            return
        self.equivalentes[idx].set(valor)
        self._actualizar_totales()

    def _actualizar_totales(self, *args):
        totales = {"kcal": 0.0, "prot": 0.0, "lip": 0.0, "hc": 0.0}
        self.total_eq = 0.0
        for i, (grupo, subgrupo, kcal, prot, lip, hc) in enumerate(
            EQUIVALENTES_DATA
        ):
            try:
                eq = float(self.equivalentes[i].get() or 0)
            except ValueError:
                eq = 0.0
            self.total_eq += eq
            valores = (
                kcal, prot, lip, hc,
            )
            fila_totales = [kcal * eq, prot * eq, lip * eq, hc * eq]
            for clave, valor in zip(("kcal", "prot", "lip", "hc"), fila_totales):
                totales[clave] += valor
            self.eq_tree.item(
                str(i),
                values=(
                    grupo, subgrupo, kcal, prot, lip, hc,
                    f"{eq:.2f}",
                    *[f"{v:.1f}" for v in fila_totales],
                ),
            )
        self.totales_eq = totales
        self._actualizar_faltantes()

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

    def sugerir_equivalentes(self):
        objetivo = self._objetivo_equivalentes()
        for i, valor in enumerate(objetivo):
            self.equivalentes[i].set(str(valor))
        self._actualizar_totales()

    def limpiar_equivalentes(self):
        for var in self.equivalentes:
            var.set("0")

    # ------------------------------------------------------------------
    def reconstruir_tiempos(self):
        for widget in self.dist_contenedor.winfo_children():
            widget.destroy()

        try:
            num = int(self.num_var.get())
        except ValueError:
            num = 4
        nombres = TIEMPOS_PREDEF.get(num, [f"Tiempo {i+1}" for i in range(num)])

        self.tiempo_vars = []
        self.tiempo_kcal_labels = []
        for t in range(num):
            fila = ttk.Frame(self.dist_contenedor, style="Gym.TFrame")
            fila.pack(fill="x", pady=1)
            var_nombre = tk.StringVar(value=nombres[t])
            ttk.Entry(fila, textvariable=var_nombre, width=20).pack(
                side=tk.LEFT, padx=4
            )
            var_pct = tk.StringVar(value=f"{100 // num}")
            var_pct.trace_add(
                "write", lambda *_a: self._actualizar_kcal_tiempos()
            )
            ttk.Label(fila, text="%:", style="Gym.TLabel").pack(
                side=tk.LEFT, padx=(8, 2)
            )
            ttk.Entry(fila, textvariable=var_pct, width=6).pack(
                side=tk.LEFT, padx=2
            )
            lbl = ttk.Label(fila, text="0 kcal", style="Estado.TLabel", width=12)
            lbl.pack(side=tk.LEFT, padx=8)
            self.tiempo_vars.append((var_nombre, var_pct))
            self.tiempo_kcal_labels.append(lbl)

        self._actualizar_kcal_tiempos()

    def _actualizar_kcal_tiempos(self):
        if not hasattr(self, "tiempo_vars") or not self.tiempo_vars:
            return
        try:
            tee = float(self.tee_var.get().replace(",", "."))
        except ValueError:
            tee = 0.0
        for (_, var_pct), lbl in zip(self.tiempo_vars, self.tiempo_kcal_labels):
            try:
                pct = float(var_pct.get().replace(",", "."))
            except ValueError:
                pct = 0.0
            lbl.configure(text=f"{tee * pct / 100:.0f} kcal")

    # ------------------------------------------------------------------
    def tomar_de_formulas(self):
        tab = getattr(self.app, "tab_formulas", None)
        if tab is None or tab.tee is None:
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

        self._actualizar_kcal_tiempos()
        self._actualizar_faltantes()


def _pedir_valor(parent, titulo, inicial):
    dialogo = tk.Toplevel(parent)
    dialogo.title(titulo)
    dialogo.configure(bg=GRIS_OSCURO)
    dialogo.transient(parent)
    dialogo.grab_set()

    ttk.Label(dialogo, text=titulo, style="Gym.TLabel").pack(
        padx=12, pady=(12, 4)
    )
    var = tk.StringVar(value=inicial)
    entry = ttk.Entry(dialogo, textvariable=var, width=12, justify="center")
    entry.pack(padx=12, pady=4)
    entry.focus_set()

    resultado = {"valor": None}

    def aceptar():
        resultado["valor"] = var.get()
        dialogo.destroy()

    barra = ttk.Frame(dialogo, style="Gym.TFrame")
    barra.pack(padx=12, pady=10)
    tk.Button(
        barra, text="ACEPTAR", command=aceptar, font=("Impact", 10), fg=NEGRO,
        bg=NEON, relief="flat", padx=12, pady=4, cursor="hand2",
    ).pack(side=tk.LEFT, padx=4)
    tk.Button(
        barra, text="CANCELAR", command=dialogo.destroy, font=("Impact", 10),
        fg=NEON, bg=GRIS, relief="flat", padx=12, pady=4, cursor="hand2",
    ).pack(side=tk.LEFT, padx=4)

    entry.bind("<Return>", lambda _e: aceptar())
    parent.wait_window(dialogo)
    return resultado["valor"]
