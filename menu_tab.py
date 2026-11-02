"""
Pestaña Menús - Elaboración de menús por día de la semana y tiempo de comida.

Toma la distribución de equivalentes por día y tiempo de la pestaña
Equivalentes (17 subgrupos SMAE-5), permite crear platillos con nombre e
ingredientes (alimentos SMAE-5 con cantidad de equivalentes) y calcula
energía + micronutrientes por tiempo de comida y por día.
"""
import io
import json
import os
import re
import tkinter as tk
import unicodedata
from tkinter import filedialog, messagebox, simpledialog, ttk

import database
import menus_print

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

# Palabras típicas de bebidas para clasificar el catálogo
_BEBIDA_RE = re.compile(
    r"\b(agua|te|licuado|jugo|nectar|cafe|atole|champurrado|limonada|"
    r"infusion|bebida|vitamina)\b"
)


def _texto_normal(s):
    t = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(
        c for c in t if unicodedata.category(c) != "Mn"
    )


def _es_bebida(nombre):
    return bool(_BEBIDA_RE.search(_texto_normal(nombre)))

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
        self._plat_catalogo = {}
        self._plat_foto = None

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

        # nombre del platillo (despliega los guardados para el tiempo actual)
        plat_bar = ttk.Frame(left, style="Gym.TFrame")
        plat_bar.pack(fill="x", pady=2)
        ttk.Label(plat_bar, text="Platillo:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.platillo_var = tk.StringVar()
        self.platillo_var.trace_add("write", self._on_platillo)
        self.platillo_combo = ttk.Combobox(
            plat_bar, textvariable=self.platillo_var, style="Gym.TCombobox",
        )
        self.platillo_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.platillo_combo.bind(
            "<<ComboboxSelected>>", self._on_platillo_seleccionado
        )
        tk.Button(
            plat_bar, text="💾 GUARDAR PLATILLO", command=self.guardar_platillo,
            font=("Impact", 8), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=8, pady=3, cursor="hand2",
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            plat_bar, text="📚 VER GUARDADOS", command=self._ventana_platillos,
            font=("Impact", 8), fg=NEON, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=8, pady=3, cursor="hand2",
        ).pack(side=tk.LEFT, padx=2)

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
        self.ing_tree.bind("<Double-1>", self._editar_eq_menu)
        self.ing_tree.bind(
            "<Delete>", lambda _e: self._eliminar_ingrediente()
        )
        self.ing_tree.tag_configure(
            "exceso", background="#4A1414", foreground="#FF6B6B",
            font=("Segoe UI", 9, "bold"),
        )
        self.menu_ing = tk.Menu(self.ing_tree, tearoff=0)
        self.menu_ing.add_command(
            label="🗑 Eliminar ingrediente",
            command=self._eliminar_ingrediente,
            font=("Segoe UI", 9),
        )
        self.menu_ing.add_separator()
        self.menu_ing.add_command(label="Cancelar")
        self.ing_tree.bind("<Button-3>", self._menu_ing_contextual)

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
        self._refrescar_platillos()
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
        hay_objetivos = any(
            self._presupuesto(idx, sg) > 0
            for sg in range(len(SUBGRUPOS_CORTO))
        )
        faltan = []
        exceden = []
        for sg_idx, corto in enumerate(SUBGRUPOS_CORTO):
            objetivo = self._presupuesto(idx, sg_idx)
            usado = sum(
                a["eq_cantidad"] * 1.0
                for a in lista
                if a["subgrupo_idx"] == sg_idx
            )
            if objetivo <= 0:
                if usado > 0 and hay_objetivos:
                    exceden.append(f"{corto} (+{usado:.2f} no distrib.)")
                continue
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
        excesos = self._excesos_idx()
        for i, reg in enumerate(lista):
            tags = ("exceso",) if reg["subgrupo_idx"] in excesos else ()
            self.ing_tree.insert(
                "", tk.END, iid=str(i), tags=tags,
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

    def _editar_eq_menu(self, _event=None):
        """Doble clic en la tabla: edita los equivalentes del
        ingrediente (de un platillo guardado o capturado) y
        actualiza los conteos del tiempo y del día."""
        sel = self.ing_tree.selection()
        if not sel:
            return
        idx = self._tiempo_idx()
        lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        pos = int(sel[0])
        if not (0 <= pos < len(lista)):
            return
        ing = lista[pos]
        respuesta = simpledialog.askstring(
            "Equivalentes",
            f"Equivalentes de {ing['alimento']}:",
            initialvalue=f"{ing['eq_cantidad']:g}",
            parent=self.marco.winfo_toplevel(),
        )
        if respuesta is None:
            return
        try:
            eq = float(respuesta.replace(",", "."))
        except ValueError:
            messagebox.showwarning("Menús", "Cantidad no válida.")
            return
        if eq <= 0:
            messagebox.showwarning("Menús", "Debe ser mayor que cero.")
            return
        ing["eq_cantidad"] = eq
        self._cargar_ingredientes()
        self._actualizar_restante()
        self._avisar_subgrupos_platillo(solo_exceso=True)

    def _excesos_idx(self):
        """Subgrupos excedidos (o sin presupuesto) en el tiempo actual."""
        idx = self._tiempo_idx()
        lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        hay_objetivos = any(
            self._presupuesto(idx, sg) > 0
            for sg in range(len(SUBGRUPOS_CORTO))
        )
        excesos = set()
        for sg_idx in range(len(SUBGRUPOS_CORTO)):
            objetivo = self._presupuesto(idx, sg_idx)
            usado = sum(
                a["eq_cantidad"] * 1.0
                for a in lista
                if a["subgrupo_idx"] == sg_idx
            )
            if usado <= 0:
                continue
            if objetivo <= 0:
                if hay_objetivos:
                    excesos.add(sg_idx)
            elif usado - 1e-9 > objetivo:
                excesos.add(sg_idx)
        return excesos

    def _menu_ing_contextual(self, event):
        """Clic derecho: menú Eliminar / Cancelar sobre la fila."""
        fila = self.ing_tree.identify_row(event.y)
        if not fila:
            return "break"
        self.ing_tree.selection_set(fila)
        self.ing_tree.focus(fila)
        try:
            self.menu_ing.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu_ing.grab_release()
        return "break"

    def _diagnostico_subgrupos(self):
        """(faltan, exceden) del tiempo actual frente a la
        distribución de Equivalentes. Un ingrediente de un subgrupo
        sin presupuesto (p. ej. aceite no distribuido) se reporta
        como exceso."""
        idx = self._tiempo_idx()
        lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        hay_objetivos = any(
            self._presupuesto(idx, sg) > 0
            for sg in range(len(SUBGRUPOS_CORTO))
        )
        faltan, exceden = [], []
        for sg_idx, corto in enumerate(SUBGRUPOS_CORTO):
            objetivo = self._presupuesto(idx, sg_idx)
            usado = sum(
                a["eq_cantidad"] * 1.0
                for a in lista
                if a["subgrupo_idx"] == sg_idx
            )
            if objetivo <= 0:
                if usado > 0 and hay_objetivos:
                    exceden.append(
                        f"{corto}: +{usado:.2f} eq (no distribuido)"
                    )
                continue
            if usado + 1e-9 < objetivo:
                faltan.append(f"{corto}: faltan {objetivo - usado:.2f} eq")
            elif usado - 1e-9 > objetivo:
                exceden.append(f"{corto}: excede +{usado - objetivo:.2f} eq")
        return faltan, exceden

    def _avisar_subgrupos_platillo(self, solo_exceso=False):
        faltan, exceden = self._diagnostico_subgrupos()
        if solo_exceso:
            faltan = []
        if not faltan and not exceden:
            return
        partes = []
        if exceden:
            partes.append("SE PASÓ DE:\n- " + "\n- ".join(exceden))
        if faltan:
            partes.append("HACE FALTA:\n- " + "\n- ".join(faltan))
        messagebox.showwarning(
            "Menús",
            "Revisa la distribución del tiempo:\n\n" + "\n\n".join(partes),
        )

    # ------------------------------------------------------------------
    # Catálogo de platillos guardados
    # ------------------------------------------------------------------
    def _refrescar_platillos(self):
        """Puebla el combo de platillos con los guardados para el tiempo actual."""
        tiempo = self.tiempo_var.get()
        platillos = database.get_platillos(tiempo) if tiempo else []
        self._platillos_tiempo = {p["nombre"]: p for p in platillos}
        self.platillo_combo["values"] = [p["nombre"] for p in platillos]

    def _on_platillo_seleccionado(self, _event=None):
        """Al elegir un platillo guardado del combo, lo agrega al menú."""
        platillo = getattr(self, "_platillos_tiempo", {}).get(
            self.platillo_var.get()
        )
        if platillo:
            self.cargar_platillo_menu(platillo)

    def cargar_platillo_menu(self, platillo):
        """Agrega (o reemplaza) los ingredientes de un platillo guardado."""
        if self.paciente_id is None:
            messagebox.showwarning("Menús", "Selecciona un paciente primero.")
            return
        try:
            ingredientes = json.loads(platillo.get("ingredientes") or "[]")
        except (json.JSONDecodeError, TypeError):
            ingredientes = []
        if not ingredientes:
            messagebox.showwarning(
                "Menús", "El platillo guardado no tiene ingredientes."
            )
            return

        idx = self._tiempo_idx()
        actuales = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        if actuales:
            reemplazar = messagebox.askyesno(
                "Menús",
                "El tiempo actual ya tiene ingredientes.\n\n"
                "¿Reemplazarlos por los del platillo?\n"
                "(Responde No para agregarlos a los existentes)",
            )
            if reemplazar:
                self.datos[self.dia_actual]["alimentos"][idx] = []
        self.datos[self.dia_actual]["alimentos"].setdefault(idx, []).extend(
            ingredientes
        )
        self._cargar_ingredientes()
        hijos = self.ing_tree.get_children()
        if hijos:
            self.ing_tree.selection_set(hijos[0])
        self._actualizar_restante()
        self._avisar_subgrupos_platillo()

    def guardar_platillo(self):
        """Abre la ventana de captura del platillo (nombre, ingredientes,
        imagen y conteo de energía/micronutrientes) para el catálogo."""
        tiempo = self.tiempo_var.get()
        if not tiempo:
            messagebox.showwarning(
                "Menús", "Selecciona (o sincroniza) un tiempo de comida."
            )
            return
        ingredientes = self.datos[self.dia_actual]["alimentos"].get(
            self._tiempo_idx(), []
        )
        if not ingredientes:
            messagebox.showwarning(
                "Menús", "Añade al menos un ingrediente antes de guardar."
            )
            return
        DialogoPlatillo(
            self, tiempo, self.platillo_var.get().strip(), ingredientes
        )

    def _ventana_platillos(self):
        """Ventana con el catálogo: imagen, ingredientes y totales."""
        ventana = tk.Toplevel(self.marco)
        ventana.title("Catálogo de platillos")
        ventana.geometry("960x580")
        ventana.configure(bg=GRIS_OSCURO)
        self._plat_ventana = ventana

        tk.Label(
            ventana, text="PLATILLOS GUARDADOS", font=("Impact", 16),
            fg=NEON, bg=GRIS_OSCURO,
        ).pack(fill="x", pady=(6, 2))

        filtro_bar = ttk.Frame(ventana, style="Gym.TFrame")
        filtro_bar.pack(fill="x", padx=8, pady=(0, 2))
        ttk.Label(filtro_bar, text="Clasificar:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(2, 4)
        )
        self._cat_filtro_var = tk.StringVar(value="Todos")
        self._cat_filtro = ttk.Combobox(
            filtro_bar, textvariable=self._cat_filtro_var,
            state="readonly", style="Gym.TCombobox", width=18,
        )
        self._cat_filtro.pack(side=tk.LEFT, padx=2)
        self._cat_filtro.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._refrescar_arbol_platillos(),
        )

        cuerpo = ttk.Frame(ventana, style="Gym.TFrame")
        cuerpo.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        izq = ttk.LabelFrame(cuerpo, text="Guardados", padding=4)
        izq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_wrap = ttk.Frame(izq, style="Gym.TFrame")
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        cols = ("nombre", "tiempo", "ing", "kcal")
        self._plat_tree = ttk.Treeview(
            tree_wrap, columns=cols, show="headings", height=14,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("nombre", "Platillo", 170),
            ("tiempo", "Tiempo", 110),
            ("ing", "Ing.", 45),
            ("kcal", "kcal", 55),
        ):
            self._plat_tree.heading(col, text=texto)
            self._plat_tree.column(col, width=ancho, anchor="center")
        self._plat_tree.column("nombre", anchor="w")
        self._plat_tree.column("tiempo", anchor="w")
        sb_tree = ttk.Scrollbar(
            tree_wrap, orient="vertical", command=self._plat_tree.yview
        )
        self._plat_tree.configure(yscrollcommand=sb_tree.set)
        self._plat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_tree.pack(side=tk.RIGHT, fill=tk.Y)
        self._plat_tree.bind(
            "<<TreeviewSelect>>", lambda _e: self._ver_detalle_platillo()
        )
        self._plat_tree.bind(
            "<Double-1>", lambda _e: self._agregar_platillo_desde_catalogo()
        )

        der = ttk.LabelFrame(cuerpo, text="Detalle", padding=4)
        der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._plat_foto_lbl = tk.Label(
            der, text="Sin imagen", bg=GRIS, fg=GRIS_TEXTO,
        )
        self._plat_foto_lbl.pack(fill="x", pady=(0, 4))
        det_wrap = ttk.Frame(der, style="Gym.TFrame")
        det_wrap.pack(fill=tk.BOTH, expand=True)
        self._plat_detalle = tk.Text(
            det_wrap, height=18, width=46, bg=GRIS, fg=BLANCO,
            font=("Segoe UI", 9), relief="flat", state="disabled",
        )
        sb_det = ttk.Scrollbar(
            det_wrap, orient="vertical", command=self._plat_detalle.yview
        )
        self._plat_detalle.configure(yscrollcommand=sb_det.set)
        self._plat_detalle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_det.pack(side=tk.RIGHT, fill=tk.Y)

        btns = ttk.Frame(ventana, style="Gym.TFrame")
        btns.pack(fill="x", padx=8, pady=6)
        tk.Button(
            btns, text="＋ AGREGAR AL MENÚ",
            command=self._agregar_platillo_desde_catalogo,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btns, text="🗑 ELIMINAR", command=self._eliminar_platillo_catalogo,
            font=("Impact", 9), fg=NEGRO, bg=NARANJA, activebackground=NEON,
            activeforeground=NEGRO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btns, text="CERRAR", command=ventana.destroy,
            font=("Impact", 9), fg=BLANCO, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)

        self._refrescar_arbol_platillos()

    def _refrescar_arbol_platillos(self):
        tree = getattr(self, "_plat_tree", None)
        if tree is None or not tree.winfo_exists():
            return
        for item in tree.get_children():
            tree.delete(item)
        self._plat_catalogo = {}
        filtro = "Todos"
        if getattr(self, "_cat_filtro_var", None) is not None:
            try:
                filtro = self._cat_filtro_var.get()
            except tk.TclError:
                filtro = "Todos"
        platillos = database.get_platillos()
        if getattr(self, "_cat_filtro", None) is not None:
            try:
                tiempos = sorted(
                    {p["tiempo_comida"] for p in platillos if p["tiempo_comida"]}
                )
                self._cat_filtro["values"] = (
                    ["Todos", "Bebidas"] + tiempos
                )
            except tk.TclError:
                pass
        for p in platillos:
            if filtro == "Bebidas":
                if not _es_bebida(p["nombre"]):
                    continue
            elif filtro != "Todos" and p["tiempo_comida"] != filtro:
                continue
            self._plat_catalogo[str(p["id_platillo"])] = p
            try:
                totales = json.loads(p.get("totales") or "{}")
                kcal = float(totales.get("energia_kcal") or 0)
            except (json.JSONDecodeError, ValueError, TypeError):
                kcal = 0.0
            try:
                n_ing = len(json.loads(p.get("ingredientes") or "[]"))
            except (json.JSONDecodeError, TypeError):
                n_ing = 0
            tree.insert(
                "", tk.END, iid=str(p["id_platillo"]),
                values=(p["nombre"], p["tiempo_comida"], n_ing, f"{kcal:.0f}"),
            )

    def _platillo_seleccionado(self):
        tree = getattr(self, "_plat_tree", None)
        if tree is None or not tree.winfo_exists():
            return None
        sel = tree.selection()
        if not sel:
            messagebox.showwarning(
                "Platillos", "Selecciona un platillo de la lista.",
                parent=self._plat_ventana,
            )
            return None
        return getattr(self, "_plat_catalogo", {}).get(sel[0])

    def _ver_detalle_platillo(self):
        platillo = self._platillo_seleccionado()
        if not platillo:
            return
        self._cargar_foto_platillo(platillo)

        try:
            ingredientes = json.loads(platillo.get("ingredientes") or "[]")
        except (json.JSONDecodeError, TypeError):
            ingredientes = []
        try:
            totales = json.loads(platillo.get("totales") or "{}")
        except (json.JSONDecodeError, TypeError):
            totales = {}

        lineas = [f"{platillo['nombre']}  ·  {platillo['tiempo_comida']}", ""]
        lineas.append("INGREDIENTES")
        for ing in ingredientes:
            sg = ing.get("subgrupo_idx", -1)
            corto = (
                SUBGRUPOS_CORTO[sg] if 0 <= sg < len(SUBGRUPOS_CORTO) else ""
            )
            try:
                eq = float(ing.get("eq_cantidad") or 0)
            except (ValueError, TypeError):
                eq = 0.0
            lineas.append(
                f"  • {ing.get('alimento', '?')} — {corto} ({eq:g} eq)"
            )
        lineas += ["", "ENERGÍA Y MICRONUTRIENTES"]
        for clave, etiqueta in MICRO_CAMPOS:
            try:
                valor = float(totales.get(clave) or 0)
            except (ValueError, TypeError):
                valor = 0.0
            lineas.append(f"  • {etiqueta}: {valor:.1f}")
        prep = (platillo.get("modo_preparacion") or "").strip()
        if prep:
            lineas += ["", "MODO DE PREPARACIÓN", prep]

        self._plat_detalle.configure(state="normal")
        self._plat_detalle.delete("1.0", tk.END)
        self._plat_detalle.insert("1.0", "\n".join(lineas))
        self._plat_detalle.configure(state="disabled")

    def _cargar_foto_platillo(self, platillo):
        self._plat_foto = None
        blob = platillo.get("imagen_blob")
        if blob and Image is not None and ImageTk is not None:
            try:
                with Image.open(io.BytesIO(blob)) as imagen:
                    copia = imagen.convert("RGB")
                copia.thumbnail((360, 220), Image.LANCZOS)
                self._plat_foto = ImageTk.PhotoImage(copia)
                self._plat_foto_lbl.configure(image=self._plat_foto, text="")
                return
            except Exception:
                pass
        self._plat_foto_lbl.configure(image="", text="Sin imagen")

    def _agregar_platillo_desde_catalogo(self):
        platillo = self._platillo_seleccionado()
        if not platillo:
            return
        if self.paciente_id is None:
            messagebox.showwarning(
                "Menús", "Selecciona un paciente primero.",
                parent=self._plat_ventana,
            )
            return
        tiempo_actual = self.tiempo_var.get()
        if platillo["tiempo_comida"] != tiempo_actual:
            aceptar = messagebox.askyesno(
                "Menús",
                f"El platillo está guardado para «{platillo['tiempo_comida']}»\n"
                f"y el tiempo actual es «{tiempo_actual or '(sin definir)'}».\n\n"
                "¿Agregarlo al tiempo actual de todos modos?",
                parent=self._plat_ventana,
            )
            if not aceptar:
                return
        self.platillo_var.set(platillo["nombre"])
        self.cargar_platillo_menu(platillo)

    def _eliminar_platillo_catalogo(self):
        platillo = self._platillo_seleccionado()
        if not platillo:
            return
        confirmar = messagebox.askyesno(
            "Platillos",
            f"¿Eliminar «{platillo['nombre']}» "
            f"({platillo['tiempo_comida']}) del catálogo?",
            parent=self._plat_ventana,
        )
        if not confirmar:
            return
        database.delete_platillo(platillo["id_platillo"])
        self._refrescar_arbol_platillos()
        self._plat_foto = None
        self._plat_foto_lbl.configure(image="", text="Sin imagen")
        self._plat_detalle.configure(state="normal")
        self._plat_detalle.delete("1.0", tk.END)
        self._plat_detalle.configure(state="disabled")
        self._refrescar_platillos()

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


class DialogoPlatillo(tk.Toplevel):
    """Captura de platillo: nombre, ingredientes, imagen, modo de
    preparación y conteo de energía/micronutrientes, para guardarlo
    en el catálogo."""

    def __init__(self, tab, tiempo, nombre, ingredientes):
        super().__init__(tab.marco)
        self.tab = tab
        self.title("Guardar platillo en el catálogo")
        self.configure(bg=GRIS_OSCURO)
        self.geometry("840x800")
        self.transient(tab.marco.winfo_toplevel())

        # copia local editable de los ingredientes del tiempo
        self.ingredientes = [dict(ing) for ing in ingredientes]
        self.imagen_blob = None
        self.imagen_nombre = None
        self.foto = None
        self.modo_inicial = ""

        # si ya existe un platillo igual guardado, partir de su imagen
        if nombre:
            existente = next(
                (p for p in database.get_platillos(tiempo)
                 if p["nombre"] == nombre),
                None,
            )
            if existente and existente.get("imagen_blob"):
                self.imagen_blob = existente["imagen_blob"]
                self.imagen_nombre = existente.get("imagen_nombre")
            if existente:
                self.modo_inicial = existente.get("modo_preparacion") or ""

        tk.Label(
            self, text="GUARDAR PLATILLO", font=("Impact", 18),
            fg=NEON, bg=GRIS_OSCURO,
        ).pack(fill="x", pady=(6, 2))

        # --- nombre y tiempo de comida ---
        fila = ttk.Frame(self, style="Gym.TFrame")
        fila.pack(fill="x", padx=8, pady=4)
        ttk.Label(fila, text="Nombre:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.nombre_var = tk.StringVar(value=nombre)
        ttk.Entry(
            fila, textvariable=self.nombre_var, style="Gym.TEntry", width=26
        ).pack(side=tk.LEFT, padx=2)
        ttk.Label(fila, text="Tiempo:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(12, 2)
        )
        self.tiempo_var = tk.StringVar(value=tiempo)
        valores = list(getattr(tab, "tiempos", []) or []) or [tiempo]
        ttk.Combobox(
            fila, textvariable=self.tiempo_var, values=valores,
            state="readonly", style="Gym.TCombobox", width=18,
        ).pack(side=tk.LEFT, padx=2)

        cuerpo = ttk.Frame(self, style="Gym.TFrame")
        cuerpo.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- izquierda: captura de ingredientes ---
        izq = ttk.LabelFrame(cuerpo, text="Ingredientes", padding=4)
        izq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        fila1 = ttk.Frame(izq, style="Gym.TFrame")
        fila1.pack(fill="x", pady=2)
        ttk.Label(fila1, text="Subgrupo:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.subgrupo_var = tk.StringVar(value=SUBGRUPOS_CORTO[0])
        self.subgrupo_combo = ttk.Combobox(
            fila1, textvariable=self.subgrupo_var, values=SUBGRUPOS_CORTO,
            state="readonly", style="Gym.TCombobox", width=17,
        )
        self.subgrupo_combo.pack(side=tk.LEFT, padx=2)
        self.subgrupo_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._cargar_alimentos()
        )

        fila2 = ttk.Frame(izq, style="Gym.TFrame")
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

        fila3 = ttk.Frame(izq, style="Gym.TFrame")
        fila3.pack(fill="x", pady=2)
        ttk.Label(fila3, text="Eq:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.eq_var = tk.StringVar(value="1")
        ttk.Spinbox(
            fila3, from_=0.25, to=50, increment=0.25, textvariable=self.eq_var,
            width=7, style="Gym.TSpinbox",
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            fila3, text="+ AÑADIR", command=self._agregar,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=10, pady=3,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            fila3, text="QUITAR SEL.", command=self._quitar,
            font=("Impact", 8), fg=NEON, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=8, pady=3,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=2)

        cols = ("alimento", "subgrupo", "eq", "kcal")
        self.tree = ttk.Treeview(
            izq, columns=cols, show="headings", height=9,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("alimento", "Ingrediente", 180),
            ("subgrupo", "Subgrupo", 100),
            ("eq", "Eq.", 40),
            ("kcal", "kcal", 55),
        ):
            self.tree.heading(col, text=texto)
            self.tree.column(col, width=ancho, anchor="center")
        self.tree.column("alimento", anchor="w")
        self.tree.column("subgrupo", anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=3)
        self.tree.bind("<Double-1>", self._editar_eq)
        ttk.Label(
            izq, text="Doble clic en un ingrediente para cambiar sus eq.",
            style="Gym.TLabel", font=("Segoe UI", 8),
        ).pack(anchor="w")

        # --- derecha: imagen y conteo nutrimental ---
        der = ttk.LabelFrame(cuerpo, text="Imagen y conteo", padding=4)
        der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.foto_lbl = tk.Label(
            der, text="Sin imagen", bg=GRIS, fg=GRIS_TEXTO,
        )
        self.foto_lbl.pack(fill="x", pady=(0, 2))
        img_btns = ttk.Frame(der, style="Gym.TFrame")
        img_btns.pack(fill="x", pady=2)
        tk.Button(
            img_btns, text="📷 SUBIR IMAGEN", command=self._subir_imagen,
            font=("Impact", 8), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=8, pady=3,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            img_btns, text="QUITAR IMAGEN", command=self._quitar_imagen,
            font=("Impact", 8), fg=NEON, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=8, pady=3,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=2)

        self.lbl_kcal = tk.Label(
            der, text="0 kcal", font=("Impact", 22), fg=NEON, bg=GRIS_OSCURO,
        )
        self.lbl_kcal.pack(pady=(8, 2))
        self.txt_totales = tk.Text(
            der, height=12, width=34, bg=GRIS, fg=BLANCO,
            font=("Segoe UI", 9), relief="flat", state="disabled",
        )
        self.txt_totales.pack(fill=tk.BOTH, expand=True, pady=2)

        # --- modo de preparación ---
        prep = ttk.LabelFrame(self, text="Modo de preparación", padding=4)
        prep.pack(fill="x", padx=8, pady=4)
        self.txt_prep = tk.Text(
            prep, height=5, bg=GRIS, fg=BLANCO, font=("Segoe UI", 9),
            relief="flat", wrap="word", insertbackground=NEON,
        )
        self.txt_prep.pack(fill=tk.BOTH, expand=True)
        if self.modo_inicial:
            self.txt_prep.insert("1.0", self.modo_inicial)

        # --- botones finales ---
        fin = ttk.Frame(self, style="Gym.TFrame")
        fin.pack(fill="x", padx=8, pady=6)
        tk.Button(
            fin, text="💾 GUARDAR AL CATÁLOGO", command=self._guardar,
            font=("Impact", 10), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=14, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)
        tk.Button(
            fin, text="CANCELAR", command=self.destroy,
            font=("Impact", 9), fg=BLANCO, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)

        self._cargar_alimentos()
        self._refrescar_arbol()
        self._mostrar_foto()
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    def _cargar_alimentos(self):
        nombre = self.subgrupo_var.get()
        if nombre not in SUBGRUPOS_CORTO:
            self._alimentos = []
        else:
            grupo = SUBGRUPOS[SUBGRUPOS_CORTO.index(nombre)]
            self._alimentos = database.get_smae_alimentos_por_grupo(grupo)
        self.alimento_combo["values"] = [a["alimento"] for a in self._alimentos]
        self.alimento_var.set("")

    def _filtrar_alimentos(self, _event=None):
        texto = self.alimento_var.get().lower()
        alimentos = getattr(self, "_alimentos", [])
        if not texto:
            self.alimento_combo["values"] = [a["alimento"] for a in alimentos]
        else:
            self.alimento_combo["values"] = [
                a["alimento"] for a in alimentos
                if texto in a["alimento"].lower()
            ]

    def _agregar(self):
        nombre = self.subgrupo_var.get()
        if nombre not in SUBGRUPOS_CORTO:
            messagebox.showwarning(
                "Platillo", "Selecciona un subgrupo.", parent=self
            )
            return
        objetivo = self.alimento_var.get().strip()
        alimento = next(
            (a for a in getattr(self, "_alimentos", [])
             if a["alimento"] == objetivo),
            None,
        )
        if alimento is None:
            messagebox.showwarning(
                "Platillo", "Selecciona un alimento de la lista.", parent=self
            )
            return
        try:
            eq = float(self.eq_var.get().replace(",", "."))
        except ValueError:
            eq = 1.0
        eq = max(eq, 0.25)

        registro = {"subgrupo_idx": SUBGRUPOS_CORTO.index(nombre),
                    "eq_cantidad": eq}
        for clave, _ in MICRO_CAMPOS:
            registro[clave] = alimento.get(clave) or 0
        registro["alimento"] = alimento["alimento"]
        registro["grupo"] = alimento["grupo"]
        registro["unidad"] = alimento.get("unidad") or ""
        registro["cantidad_sugerida"] = alimento.get("cantidad_sugerida") or 0
        registro["peso_bruto_g"] = alimento.get("peso_bruto_g") or 0
        registro["peso_neto_g"] = alimento.get("peso_neto_g") or 0
        self.ingredientes.append(registro)
        self.alimento_var.set("")
        self._refrescar_arbol()

    def _quitar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Platillo", "Selecciona un ingrediente.", parent=self
            )
            return
        pos = int(sel[0])
        if 0 <= pos < len(self.ingredientes):
            self.ingredientes.pop(pos)
        self._refrescar_arbol()

    def _editar_eq(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        pos = int(sel[0])
        if not (0 <= pos < len(self.ingredientes)):
            return
        ing = self.ingredientes[pos]
        respuesta = simpledialog.askstring(
            "Equivalentes",
            f"Equivalentes de {ing['alimento']}:",
            initialvalue=f"{ing['eq_cantidad']:g}",
            parent=self,
        )
        if respuesta is None:
            return
        try:
            eq = float(respuesta.replace(",", "."))
        except ValueError:
            messagebox.showwarning(
                "Platillo", "Cantidad no válida.", parent=self
            )
            return
        if eq <= 0:
            messagebox.showwarning(
                "Platillo", "Debe ser mayor que cero.", parent=self
            )
            return
        ing["eq_cantidad"] = eq
        self._refrescar_arbol()

    def _refrescar_arbol(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, reg in enumerate(self.ingredientes):
            sg = reg.get("subgrupo_idx", -1)
            corto = (
                SUBGRUPOS_CORTO[sg] if 0 <= sg < len(SUBGRUPOS_CORTO) else ""
            )
            self.tree.insert(
                "", tk.END, iid=str(i),
                values=(
                    reg["alimento"], corto, f"{reg['eq_cantidad']:g}",
                    f"{(reg.get('energia_kcal') or 0) * reg['eq_cantidad']:.1f}",
                ),
            )
        self._actualizar_totales()

    def _actualizar_totales(self):
        totales = self.tab._sumar(self.ingredientes)
        self.lbl_kcal.configure(text=f"{totales['energia_kcal']:.0f} kcal")
        lineas = []
        for clave, etiqueta in MICRO_CAMPOS:
            if clave == "energia_kcal":
                continue
            lineas.append(f"  • {etiqueta}: {totales[clave]:.1f}")
        self.txt_totales.configure(state="normal")
        self.txt_totales.delete("1.0", tk.END)
        self.txt_totales.insert("1.0", "\n".join(lineas))
        self.txt_totales.configure(state="disabled")

    def _subir_imagen(self):
        ruta = filedialog.askopenfilename(
            parent=self, title="Imagen del platillo",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not ruta:
            return
        try:
            with open(ruta, "rb") as archivo:
                self.imagen_blob = archivo.read()
            self.imagen_nombre = os.path.basename(ruta)
        except OSError as error:
            messagebox.showerror(
                "Platillo", f"No se pudo leer la imagen:\n{error}", parent=self
            )
            return
        self._mostrar_foto()

    def _quitar_imagen(self):
        self.imagen_blob = None
        self.imagen_nombre = None
        self.foto = None
        self.foto_lbl.configure(image="", text="Sin imagen")

    def _mostrar_foto(self):
        if self.imagen_blob and Image is not None and ImageTk is not None:
            try:
                with Image.open(io.BytesIO(self.imagen_blob)) as imagen:
                    copia = imagen.convert("RGB")
                copia.thumbnail((300, 190), Image.LANCZOS)
                self.foto = ImageTk.PhotoImage(copia)
                self.foto_lbl.configure(image=self.foto, text="")
                return
            except Exception:
                pass
        self.foto = None
        self.foto_lbl.configure(image="", text="Sin imagen")

    def _guardar(self):
        nombre = self.nombre_var.get().strip()
        tiempo = self.tiempo_var.get().strip()
        if not nombre:
            messagebox.showwarning(
                "Platillo", "Escribe el nombre del platillo.", parent=self
            )
            return
        if not tiempo:
            messagebox.showwarning(
                "Platillo", "Selecciona el tiempo de comida.", parent=self
            )
            return
        if not self.ingredientes:
            messagebox.showwarning(
                "Platillo", "Añade al menos un ingrediente.", parent=self
            )
            return
        totales = self.tab._sumar(self.ingredientes)
        database.guardar_platillo({
            "nombre": nombre,
            "tiempo_comida": tiempo,
            "ingredientes": json.dumps(self.ingredientes, ensure_ascii=False),
            "totales": json.dumps(totales, ensure_ascii=False),
            "modo_preparacion": self.txt_prep.get("1.0", "end").strip(),
            "imagen_nombre": self.imagen_nombre,
            "imagen_blob": self.imagen_blob,
        })
        self.tab._refrescar_platillos()
        if tiempo == self.tab.tiempo_var.get():
            self.tab.platillo_var.set(nombre)
        self.destroy()
        messagebox.showinfo(
            "Platillo",
            f"«{nombre}» guardado en el catálogo ({tiempo}).\n"
            f"{len(self.ingredientes)} ingredientes · "
            f"{totales['energia_kcal']:.0f} kcal\n\n"
            "Ya puedes seleccionarlo en el campo Platillo de ese tiempo.",
        )
