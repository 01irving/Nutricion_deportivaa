"""
Pestaña Menús - Elaboración de menús por día de la semana y tiempo de comida.

Toma la distribución de equivalentes por día y tiempo de la pestaña
Equivalentes (17 subgrupos SMAE-5), permite crear platillos con nombre e
ingredientes (alimentos SMAE-5 con cantidad de equivalentes) y calcula
energía + micronutrientes por tiempo de comida y por día.
"""
import json
import tkinter as tk
from tkinter import messagebox, ttk

import database
import menus_print

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

DIAS_SEMANA = [
    "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo",
]

# Subgrupos SMAE-5 (índice alineado con EQUIVALENTES_DATA de equivalentes_tab)
SUBGRUPOS = [
    "Verduras",
    "Frutas",
    "Cereales sin grasa",
    "Cereales con grasa",
    "Leguminosas",
    "AOA MBAG",
    "AOA BAG",
    "AOA MAG",
    "AOA AAG",
    "Leche descremada",
    "Leche semidescremada",
    "Leche entera",
    "Leche con azúcar",
    "Aceites y grasas",
    "Aceites y grasas con proteina",
    "Azucares sin grasa",
    "Azucares con grasa",
]

# Nombre corto de cada subgrupo para las etiquetas del menú
SUBGRUPOS_CORTO = [
    "Verduras", "Frutas", "Cereales s/g", "Cereales c/g", "Leguminosas",
    "AOA MBAG", "AOA BAG", "AOA MAG", "AOA AAG",
    "Leche descrem.", "Leche semidesc.", "Leche entera", "Leche azúcar",
    "Grasas s/prot", "Grasas c/prot", "Azúcares s/g", "Azúcares c/g",
]

# (columna_bd, etiqueta) - nutrientes contados por tiempo y por día
MICRO_CAMPOS = [
    ("energia_kcal", "Energía (kcal)"),
    ("proteina_g", "Proteína (g)"),
    ("lipidos_g", "Lípidos (g)"),
    ("hc_g", "HC (g)"),
    ("fibra_g", "Fibra (g)"),
    ("azucar_g", "Azúcares (g)"),
    ("vitamina_a_ug", "Vit. A (µg)"),
    ("vitamina_c_mg", "Vit. C (mg)"),
    ("acido_folico_ug", "Ác. Fólico (µg)"),
    ("hierro_mg", "Hierro (mg)"),
    ("calcio_mg", "Calcio (mg)"),
    ("potasio_mg", "Potasio (mg)"),
    ("sodio_mg", "Sodio (mg)"),
]


class MenusTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self.dia_actual = DIAS_SEMANA[0]
        # {dia: {"platillos": {tiempo_idx: str}, "alimentos": {tiempo_idx: [dict]}}}
        self.datos = {dia: {"platillos": {}, "alimentos": {}} for dia in DIAS_SEMANA}
        self.sel_alimento = None

    # ------------------------------------------------------------------
    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  🍲 Menús  ")

        titulo = tk.Label(
            self.marco,
            text="MENÚS POR DÍA Y TIEMPO DE COMIDA",
            font=("Impact", 20), fg=NEON, bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 2))

        self.lbl_estado = ttk.Label(
            self.marco, text="Menús: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        # --- Selector de día ---
        dias_bar = ttk.Frame(self.marco, style="Gym.TFrame")
        dias_bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Label(dias_bar, text="Día:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(0, 6)
        )
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

        tk.Button(
            dias_bar, text="ACTUALIZAR DISTRIBUCIÓN",
            command=self.sincronizar_distribucion,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=10, pady=3, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)
        tk.Button(
            dias_bar, text="GUARDAR MENÚ", command=self.guardar,
            font=("Impact", 9), fg=NEGRO, bg=NARANJA, activebackground=NEON,
            activeforeground=NEGRO, relief="flat", padx=10, pady=3, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)
        tk.Button(
            dias_bar, text="IMPRIMIR", command=self.imprimir,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=10, pady=3, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)

        # --- Panel de tiempo de comida (izquierda) ---
        paned = ttk.PanedWindow(self.marco, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._crear_panel_tiempo(paned)
        self._crear_panel_totales(paned)
        self._resaltar_dia()

    def _crear_panel_tiempo(self, paned):
        left = ttk.LabelFrame(paned, text="Platillo e ingredientes", padding=5)
        paned.add(left, weight=2)

        # selector de tiempo de comida
        tiem_bar = ttk.Frame(left, style="Gym.TFrame")
        tiem_bar.pack(fill="x", pady=2)
        ttk.Label(tiem_bar, text="Tiempo:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.tiempo_var = tk.StringVar()
        self.tiempo_combo = ttk.Combobox(
            tiem_bar, textvariable=self.tiempo_var, state="readonly",
            style="Gym.TCombobox", width=30,
        )
        self.tiempo_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.tiempo_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._render_tiempo()
        )

        # nombre del platillo
        plat_bar = ttk.Frame(left, style="Gym.TFrame")
        plat_bar.pack(fill="x", pady=2)
        ttk.Label(plat_bar, text="Platillo:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.platillo_var = tk.StringVar()
        self.platillo_var.trace_add("write", self._on_platillo)
        ttk.Entry(plat_bar, textvariable=self.platillo_var,
                  style="Gym.TEntry").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )

        # selector de ingrediente (alimento SMAE-5)
        ing_frame = ttk.LabelFrame(left, text="Ingrediente (SMAE-5)", padding=5)
        ing_frame.pack(fill="x", pady=3)

        fila1 = ttk.Frame(ing_frame, style="Gym.TFrame")
        fila1.pack(fill="x", pady=2)
        ttk.Label(fila1, text="Subgrupo:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.subgrupo_var = tk.StringVar()
        self.subgrupo_combo = ttk.Combobox(
            fila1, textvariable=self.subgrupo_var, state="readonly",
            values=SUBGRUPOS_CORTO, style="Gym.TCombobox", width=18,
        )
        self.subgrupo_combo.pack(side=tk.LEFT, padx=2)
        self.subgrupo_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._cargar_alimentos_subgrupo()
        )
        self.rest_label = tk.Label(
            fila1, text="", fg=NEON, bg=GRIS_OSCURO, font=("Segoe UI", 9)
        )
        self.rest_label.pack(side=tk.LEFT, padx=8)

        fila2 = ttk.Frame(ing_frame, style="Gym.TFrame")
        fila2.pack(fill="x", pady=2)
        ttk.Label(fila2, text="Alimento:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.alimento_var = tk.StringVar()
        self.alimento_combo = ttk.Combobox(
            fila2, textvariable=self.alimento_var, state="normal",
            style="Gym.TCombobox",
        )
        self.alimento_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.alimento_combo.bind("<KeyRelease>", self._filtrar_alimentos)

        fila3 = ttk.Frame(ing_frame, style="Gym.TFrame")
        fila3.pack(fill="x", pady=2)
        ttk.Label(fila3, text="Equivalentes:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.eq_var = tk.StringVar(value="1")
        ttk.Spinbox(
            fila3, from_=0.25, to=50, increment=0.25, textvariable=self.eq_var,
            width=8, style="Gym.TSpinbox",
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            fila3, text="+ AÑADIR", command=self._agregar_ingrediente,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=3, cursor="hand2",
        ).pack(side=tk.LEFT, padx=8)

        # lista de ingredientes del tiempo actual
        cols = ("alimento", "subgrupo", "eq", "kcal", "prot", "lip", "hc")
        self.ing_tree = ttk.Treeview(
            left, columns=cols, show="headings", height=12,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("alimento", "Ingrediente", 190),
            ("subgrupo", "Subgrupo", 120),
            ("eq", "Eq.", 45),
            ("kcal", "kcal", 60),
            ("prot", "Prot", 50),
            ("lip", "Lip", 50),
            ("hc", "HC", 50),
        ):
            self.ing_tree.heading(col, text=texto)
            self.ing_tree.column(col, width=ancho, anchor="center")
        self.ing_tree.column("alimento", anchor="w")
        self.ing_tree.column("subgrupo", anchor="w")
        self.ing_tree.pack(fill="both", expand=True, pady=3)

        btns = ttk.Frame(left, style="Gym.TFrame")
        btns.pack(fill="x", pady=2)
        for texto, cmd in (
            ("ELIMINAR SELECCIONADO", self._eliminar_ingrediente),
            ("LIMPIAR TIEMPO", self._limpiar_tiempo),
        ):
            tk.Button(
                btns, text=texto, command=cmd, font=("Impact", 9), fg=NEON,
                bg=GRIS, activebackground=NARANJA, activeforeground=BLANCO,
                relief="flat", padx=10, pady=3, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)

    def _crear_panel_totales(self, paned):
        right = ttk.LabelFrame(paned, text="Totales", padding=5)
        paned.add(right, weight=1)

        ttk.Label(
            right, text="TIEMPO ACTUAL", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.tot_tiempo = {}
        for clave, etiqueta in MICRO_CAMPOS:
            self.tot_tiempo[clave] = self._fila_total(right, etiqueta, NEON)

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        ttk.Label(
            right, text="TOTAL DEL DÍA", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.tot_dia = {}
        for clave, etiqueta in MICRO_CAMPOS:
            self.tot_dia[clave] = self._fila_total(right, etiqueta, NEON)

    def _fila_total(self, parent, etiqueta, color):
        row = ttk.Frame(parent, style="Gym.TFrame")
        row.pack(fill=tk.X, padx=5)
        ttk.Label(row, text=etiqueta, style="Gym.TLabel", width=16,
                  anchor=tk.W).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="0", fg=color, bg=GRIS_OSCURO, width=10,
                       anchor=tk.E)
        lbl.pack(side=tk.RIGHT)
        return lbl

    # ------------------------------------------------------------------
    # Distribución (desde la pestaña Equivalentes)
    # ------------------------------------------------------------------
    def _dist_tab(self):
        return getattr(self.app, "tab_equivalentes", None)

    def sincronizar_distribucion(self):
        """Copia los tiempos y la distribución por día desde Equivalentes."""
        tab = self._dist_tab()
        if tab is None:
            return
        nombres = [v.get() for v in getattr(tab, "dist_nombres_vars", [])]
        if not nombres:
            messagebox.showinfo(
                "Menús",
                "Primero define la distribución por tiempos en la pestaña "
                "Equivalentes.",
            )
            return
        self.tiempos = nombres
        self.tiempo_combo["values"] = nombres
        if self.tiempo_var.get() not in nombres:
            self.tiempo_var.set(nombres[0])
        self._render_tiempo()

    def _presupuesto(self, tiempo_idx, subgrupo_idx):
        """Equivalentes objetivo para (día, tiempo, subgrupo) desde Equivalentes."""
        tab = self._dist_tab()
        if tab is None:
            return 0.0
        valores = tab.dist_datos.get(self.dia_actual, {}).get("valores") or []
        if subgrupo_idx < len(valores):
            fila = valores[subgrupo_idx]
            if tiempo_idx < len(fila):
                try:
                    return float(fila[tiempo_idx] or 0)
                except (ValueError, TypeError):
                    return 0.0
        return 0.0

    def _subgrupos_disponibles(self, tiempo_idx):
        """Nombres cortos de subgrupos con presupuesto > 0 en (día, tiempo)."""
        return [
            corto
            for sg_idx, corto in enumerate(SUBGRUPOS_CORTO)
            if self._presupuesto(tiempo_idx, sg_idx) > 0
        ]

    def _refrescar_subgrupos(self):
        """Puebla el combo de subgrupos solo con los distribuidos."""
        idx = self._tiempo_idx()
        disponibles = self._subgrupos_disponibles(idx)
        self.subgrupo_combo["values"] = disponibles
        if self.subgrupo_var.get() not in disponibles:
            self.subgrupo_var.set(disponibles[0] if disponibles else "")
            self._cargar_alimentos_subgrupo()

    # ------------------------------------------------------------------
    # Día / tiempo
    # ------------------------------------------------------------------
    def _cambiar_dia(self, dia):
        if dia == self.dia_actual:
            return
        self.dia_actual = dia
        self._resaltar_dia()
        self.sincronizar_distribucion()
        self._render_tiempo()
        self._actualizar_totales()

    def _resaltar_dia(self):
        for dia, btn in self.dia_buttons.items():
            seleccionado = dia == self.dia_actual
            btn.configure(
                bg=NEON if seleccionado else GRIS,
                fg=NEGRO if seleccionado else BLANCO,
            )

    def _tiempo_idx(self):
        tiempos = getattr(self, "tiempos", [])
        nombre = self.tiempo_var.get()
        return tiempos.index(nombre) if nombre in tiempos else 0

    def _on_platillo(self, *args):
        idx = self._tiempo_idx()
        self.datos[self.dia_actual]["platillos"][idx] = self.platillo_var.get()

    def _render_tiempo(self):
        idx = self._tiempo_idx()
        self.platillo_var.set(
            self.datos[self.dia_actual]["platillos"].get(idx, "")
        )
        self._refrescar_subgrupos()
        self._cargar_ingredientes()
        self._actualizar_restante()

    def _cargar_alimentos_subgrupo(self):
        nombre = self.subgrupo_var.get()
        if nombre not in SUBGRUPOS_CORTO:
            self._alimentos_subgrupo = []
            self.alimento_combo["values"] = []
            self.alimento_var.set("")
            return
        grupo = SUBGRUPOS[SUBGRUPOS_CORTO.index(nombre)]
        alimentos = database.get_smae_alimentos_por_grupo(grupo)
        self._alimentos_subgrupo = alimentos
        self.alimento_combo["values"] = [a["alimento"] for a in alimentos]
        self.alimento_var.set("")
        self._actualizar_restante()

    def _filtrar_alimentos(self, _event=None):
        texto = self.alimento_var.get().lower()
        alimentos = getattr(self, "_alimentos_subgrupo", [])
        if not texto:
            self.alimento_combo["values"] = [a["alimento"] for a in alimentos]
        else:
            self.alimento_combo["values"] = [
                a["alimento"] for a in alimentos
                if texto in a["alimento"].lower()
            ]

    def _actualizar_restante(self):
        if not hasattr(self, "rest_label"):
            return
        nombre = self.subgrupo_var.get()
        if nombre not in SUBGRUPOS_CORTO:
            self.rest_label.configure(text=self._resumen_faltantes())
            return
        sg_idx = SUBGRUPOS_CORTO.index(nombre)
        idx = self._tiempo_idx()
        presupuesto = self._presupuesto(idx, sg_idx)
        usado = sum(
            a["eq_cantidad"] * 1.0
            for a in self.datos[self.dia_actual]["alimentos"].get(idx, [])
            if a["subgrupo_idx"] == sg_idx
        )
        restante = presupuesto - usado
        faltante = max(0.0, restante)
        exceso = max(0.0, -restante)
        if exceso > 1e-9:
            self.rest_label.configure(
                text=f"EXCEDE {exceso:.2f} de {presupuesto:.1f}", fg=NARANJA
            )
        else:
            self.rest_label.configure(
                text=f"({faltante:.2f} disp de {presupuesto:.1f})",
                fg=NEON if faltante > 0 else NARANJA,
            )

    def _resumen_faltantes(self):
        """Resumen de subgrupos con equivalentes faltantes o excedidos."""
        idx = self._tiempo_idx()
        lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        faltan = []
        exceden = []
        for sg_idx, corto in enumerate(SUBGRUPOS_CORTO):
            objetivo = self._presupuesto(idx, sg_idx)
            if objetivo <= 0:
                continue
            usado = sum(
                a["eq_cantidad"] * 1.0
                for a in lista
                if a["subgrupo_idx"] == sg_idx
            )
            if usado + 1e-9 < objetivo:
                faltan.append(f"{corto} ({objetivo - usado:.2f})")
            elif usado - 1e-9 > objetivo:
                exceden.append(f"{corto} (+{usado - objetivo:.2f})")
        if exceden:
            return "EXCEDE: " + ", ".join(exceden)
        if faltan:
            return "FALTAN: " + ", ".join(faltan)
        return "COMPLETO"

    # ------------------------------------------------------------------
    # Ingredientes
    # ------------------------------------------------------------------
    def _agregar_ingrediente(self):
        if self.paciente_id is None:
            messagebox.showwarning("Menús", "Selecciona un paciente primero.")
            return
        nombre = self.subgrupo_var.get()
        if nombre not in SUBGRUPOS_CORTO:
            messagebox.showwarning("Menús", "Selecciona un subgrupo.")
            return
        sg_idx = SUBGRUPOS_CORTO.index(nombre)
        objetivo = self.alimento_var.get().strip()
        if not objetivo:
            messagebox.showwarning("Menús", "Selecciona un alimento.")
            return
        alimentos = getattr(self, "_alimentos_subgrupo", [])
        alimento = next(
            (a for a in alimentos if a["alimento"] == objetivo), None
        )
        if alimento is None:
            messagebox.showwarning("Menús", "Alimento no encontrado en el grupo.")
            return
        try:
            eq = float(self.eq_var.get().replace(",", "."))
        except ValueError:
            eq = 1.0
        if eq <= 0:
            eq = 1.0

        idx = self._tiempo_idx()
        presupuesto = self._presupuesto(idx, sg_idx)
        usado = sum(
            a["eq_cantidad"] * 1.0
            for a in self.datos[self.dia_actual]["alimentos"].get(idx, [])
            if a["subgrupo_idx"] == sg_idx
        )
        restante = presupuesto - usado
        if presupuesto > 0 and eq > restante + 1e-9:
            messagebox.showwarning(
                "Menús",
                f"El subgrupo {SUBGRUPOS_CORTO[sg_idx]} excede el presupuesto "
                f"del tiempo.\nObjetivo: {presupuesto:.2f} eq  |  "
                f"Usado: {usado:.2f} eq  |  Disponible: {max(0.0, restante):.2f} eq.\n"
                f"Intenta con {max(0.0, restante):.2f} eq o menos.",
            )
            return

        registro = {"subgrupo_idx": sg_idx, "eq_cantidad": eq}
        for clave, _ in MICRO_CAMPOS:
            registro[clave] = alimento.get(clave) or 0
        registro["alimento"] = alimento["alimento"]
        registro["grupo"] = alimento["grupo"]
        registro["unidad"] = alimento.get("unidad") or ""
        registro["cantidad_sugerida"] = alimento.get("cantidad_sugerida") or 0
        registro["peso_bruto_g"] = alimento.get("peso_bruto_g") or 0
        registro["peso_neto_g"] = alimento.get("peso_neto_g") or 0

        self.datos[self.dia_actual]["alimentos"].setdefault(idx, []).append(registro)
        self._cargar_ingredientes()
        self.alimento_var.set("")
        self._actualizar_restante()

    def _cargar_ingredientes(self):
        for item in self.ing_tree.get_children():
            self.ing_tree.delete(item)
        idx = self._tiempo_idx()
        lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        for i, reg in enumerate(lista):
            self.ing_tree.insert(
                "", tk.END, iid=str(i),
                values=(
                    reg["alimento"],
                    SUBGRUPOS_CORTO[reg["subgrupo_idx"]],
                    f"{reg['eq_cantidad']:g}",
                    f"{(reg.get('energia_kcal') or 0) * reg['eq_cantidad']:.1f}",
                    f"{(reg.get('proteina_g') or 0) * reg['eq_cantidad']:.1f}",
                    f"{(reg.get('lipidos_g') or 0) * reg['eq_cantidad']:.1f}",
                    f"{(reg.get('hc_g') or 0) * reg['eq_cantidad']:.1f}",
                ),
            )
        self._actualizar_totales()

    def _eliminar_ingrediente(self):
        sel = self.ing_tree.selection()
        if not sel:
            messagebox.showwarning("Menús", "Selecciona un ingrediente.")
            return
        idx = self._tiempo_idx()
        lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        pos = int(sel[0])
        if 0 <= pos < len(lista):
            lista.pop(pos)
        self._cargar_ingredientes()
        self._actualizar_restante()

    def _limpiar_tiempo(self):
        idx = self._tiempo_idx()
        self.datos[self.dia_actual]["alimentos"][idx] = []
        self.datos[self.dia_actual]["platillos"][idx] = ""
        self.platillo_var.set("")
        self._cargar_ingredientes()
        self._actualizar_restante()

    # ------------------------------------------------------------------
    # Totales
    # ------------------------------------------------------------------
    def _sumar(self, lista):
        totales = {clave: 0.0 for clave, _ in MICRO_CAMPOS}
        for reg in lista:
            eq = reg.get("eq_cantidad", 1.0)
            for clave, _ in MICRO_CAMPOS:
                try:
                    totales[clave] += float(reg.get(clave) or 0) * eq
                except (ValueError, TypeError):
                    pass
        return totales

    def _actualizar_totales(self):
        idx = self._tiempo_idx()
        alimentos = self.datos[self.dia_actual]["alimentos"]
        tot_tiempo = self._sumar(alimentos.get(idx, []))
        for clave, lbl in self.tot_tiempo.items():
            lbl.configure(text=f"{tot_tiempo[clave]:.1f}")

        todos = []
        for lista in alimentos.values():
            todos.extend(lista)
        tot_dia = self._sumar(todos)
        for clave, lbl in self.tot_dia.items():
            lbl.configure(text=f"{tot_dia[clave]:.1f}")

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def guardar(self):
        if self.paciente_id is None:
            messagebox.showwarning("Menús", "Selecciona un paciente antes de guardar.")
            return
        datos = {
            "tiempos": getattr(self, "tiempos", []),
            "dias": {
                dia: {
                    "platillos": {
                        str(k): v
                        for k, v in self.datos[dia]["platillos"].items() if v
                    },
                    "alimentos": {
                        str(k): v
                        for k, v in self.datos[dia]["alimentos"].items() if v
                    },
                }
                for dia in DIAS_SEMANA
            },
        }
        database.guardar_menu(
            self.paciente_id, json.dumps(datos, ensure_ascii=False)
        )
        aviso = self._revisar_presupuestos_dia()
        if aviso:
            messagebox.showwarning(
                "Menús",
                "Menú guardado, pero hay diferencias con la distribución:\n\n"
                + aviso,
            )
        else:
            messagebox.showinfo("Menús", "Menú guardado para el paciente activo.")

    def _revisar_presupuestos_dia(self):
        """Devuelve un texto con faltantes/excesos del día actual, o vacío."""
        alimentos = self.datos[self.dia_actual]["alimentos"]
        tiempos = getattr(self, "tiempos", [])
        lineas = []
        for t_idx, nombre in enumerate(tiempos):
            lista = alimentos.get(t_idx, [])
            faltan = []
            exceden = []
            for sg_idx, corto in enumerate(SUBGRUPOS_CORTO):
                objetivo = self._presupuesto(t_idx, sg_idx)
                if objetivo <= 0:
                    continue
                usado = sum(
                    a["eq_cantidad"] * 1.0
                    for a in lista
                    if a["subgrupo_idx"] == sg_idx
                )
                if usado + 1e-9 < objetivo:
                    faltan.append(f"{corto} ({objetivo - usado:.2f})")
                elif usado - 1e-9 > objetivo:
                    exceden.append(f"{corto} (+{usado - objetivo:.2f})")
            if faltan or exceden:
                partes = []
                if faltan:
                    partes.append("faltan: " + ", ".join(faltan))
                if exceden:
                    partes.append("excede: " + ", ".join(exceden))
                lineas.append(f"• {nombre}: " + " | ".join(partes))
        return "\n".join(lineas)

    def imprimir(self):
        """Genera el PDF del menú semanal y lo abre en Acrobat."""
        if self.paciente_id is None:
            messagebox.showwarning(
                "Menús", "Selecciona un paciente antes de imprimir."
            )
            return

        dias = {}
        for dia in DIAS_SEMANA:
            info = self.datos.get(dia) or {}
            dias[dia] = {
                "platillos": dict(info.get("platillos") or {}),
                "alimentos": dict(info.get("alimentos") or {}),
            }

        paciente = database.obtener_paciente(self.paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{self.paciente_id}"
        ruta = menus_print.ruta_temporal_pdf(nombre)
        try:
            menus_print.generar_pdf_menus(
                ruta, paciente, getattr(self, "tiempos", []), dias
            )
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            menus_print.abrir_para_imprimir(ruta)
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
        self.paciente_id = paciente_id
        registro = database.get_menu(paciente_id)
        self.lbl_estado.configure(text=f"Menús de paciente {paciente_id}")
        self.datos = {dia: {"platillos": {}, "alimentos": {}} for dia in DIAS_SEMANA}
        tiempos = []
        if registro:
            try:
                datos = json.loads(registro.get("detalle") or "{}")
            except (json.JSONDecodeError, TypeError):
                datos = {}
            tiempos = datos.get("tiempos") or []
            for dia in DIAS_SEMANA:
                info = datos.get("dias", {}).get(dia)
                if not info:
                    continue
                self.datos[dia]["platillos"] = {
                    int(k): v for k, v in (info.get("platillos") or {}).items()
                }
                self.datos[dia]["alimentos"] = {
                    int(k): v for k, v in (info.get("alimentos") or {}).items()
                }
        if tiempos:
            self.tiempos = tiempos
            self.tiempo_combo["values"] = tiempos
            self.tiempo_var.set(tiempos[0])
        else:
            self.sincronizar_distribucion()
        self._render_tiempo()
        self._actualizar_totales()

    def limpiar(self):
        self.paciente_id = None
        self.datos = {dia: {"platillos": {}, "alimentos": {}} for dia in DIAS_SEMANA}
        self.lbl_estado.configure(text="Menús: sin paciente seleccionado")
