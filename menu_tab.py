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
import voz

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

# Categorías para agrupar los menús guardados
CATEGORIAS_MENU = [
    "Vegano", "Vegetariano", "Clásicos", "Sin Gluten", "De actualidad",
]


def _categoria_de_menu(nombre):
    """Categoría de un menú a partir de su nombre (prefijo o palabras)."""
    nombre = str(nombre or "")
    if " · " in nombre:
        prefijo = nombre.split(" · ")[0].strip()
        for cat in CATEGORIAS_MENU:
            if prefijo.lower() == cat.lower():
                return cat
    texto = nombre.lower()
    if "vegano" in texto:
        return "Vegano"
    if "vegetariano" in texto:
        return "Vegetariano"
    if "sin gluten" in texto:
        return "Sin Gluten"
    if "actualidad" in texto:
        return "De actualidad"
    return "Clásicos"

# Palabras típicas de bebidas para clasificar el catálogo
_BEBIDA_RE = re.compile(
    r"\b(agua|te|licuado|jugo|nectar|cafe|atole|champurrado|limonada|"
    r"infusion|bebida|vitamina)\b"
)

# Smoothies (admite la variante "smothie") para el clasificador
_SMOOTHIE_RE = re.compile(r"\bsmoo?thi(e|y)s?\b")


def _texto_normal(s):
    t = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(
        c for c in t if unicodedata.category(c) != "Mn"
    )


def _es_bebida(nombre):
    return bool(_BEBIDA_RE.search(_texto_normal(nombre)))


def _es_smoothie(nombre):
    return bool(_SMOOTHIE_RE.search(_texto_normal(nombre)))

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
        # {(dia, tiempo_idx): [{"nombre": str, "ingredientes": [dict]}, ...]}
        self.platillos_partes = {}
        self._parte_activa_idx = None
        self._sync_platillo = False
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
            dias_bar, text="CARGAR MENÚ", command=self.guardar,
            font=("Impact", 9), fg=NEGRO, bg=NARANJA, activebackground=NEON,
            activeforeground=NEGRO, relief="flat", padx=10, pady=3, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)
        tk.Button(
            dias_bar, text="📂 MENÚS GUARDADOS",
            command=self._ventana_menus_guardados,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=10, pady=3, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)
        tk.Button(
            dias_bar, text="IMPRIMIR", command=self.imprimir,
            font=("Impact", 9), fg=NEGRO, bg=NARANJA, activebackground=NEON,
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
        self._marco_izq = left

        # --- Menú: desplegable principal (carga directa) ---
        men_bar = ttk.Frame(left, style="Gym.TFrame")
        men_bar.pack(fill="x", pady=(0, 2))
        ttk.Label(men_bar, text="Menú:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.menu_smae_combo = ttk.Combobox(
            men_bar, style="Gym.TCombobox",
        )
        self.menu_smae_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.menu_smae_combo.bind(
            "<<ComboboxSelected>>", self._cargar_menu_smae
        )
        self.menu_smae_combo.bind("<Return>", self._aplicar_texto_menu)
        self.menu_smae_combo.bind("<FocusOut>", self._aplicar_texto_menu)
        tk.Button(
            men_bar, text="▾", command=self._abrir_arbol_menus,
            font=("Segoe UI", 10, "bold"), fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=6, pady=1, cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 2))
        self._refrescar_combo_menus_smae()
        guardar_bar = ttk.Frame(left, style="Gym.TFrame")
        guardar_bar.pack(fill="x", pady=(0, 3))
        tk.Button(
            guardar_bar, text="💾 GUARDAR MENÚ",
            command=self._guardar_menu_nuevo,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=10, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=2)

        # selector de tiempo de comida (debajo del menú)
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

        # --- Tabla: platillos del menú guardado (tiempo actual) ---
        marco_pm = ttk.Frame(left, style="Gym.TFrame")
        marco_pm.pack(fill="x", pady=(0, 2))
        self.platillos_menu_tree = ttk.Treeview(
            marco_pm, columns=("eq",), show="tree headings", height=4,
            style="Gym.Treeview", selectmode="browse",
        )
        self.platillos_menu_tree.heading("#0", text="Platillos del menú")
        self.platillos_menu_tree.column("#0", width=215, anchor=tk.W)
        self.platillos_menu_tree.heading("eq", text="Eq. total")
        self.platillos_menu_tree.column("eq", width=60, anchor=tk.CENTER)
        bar_pm = ttk.Scrollbar(
            marco_pm, orient=tk.VERTICAL, command=self.platillos_menu_tree.yview
        )
        self.platillos_menu_tree.configure(yscrollcommand=bar_pm.set)
        self.platillos_menu_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        bar_pm.pack(side=tk.RIGHT, fill=tk.Y)
        self.platillos_menu_tree.bind(
            "<<TreeviewSelect>>", self._on_platillos_menu_select
        )
        self.platillos_menu_tree.bind(
            "<Button-3>", self._menu_plat_contextual
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
            ("alimento", "Alimento", 190),
            ("subgrupo", "Grupo", 120),
            ("eq", "Porción", 55),
            ("kcal", "Energía", 62),
            ("prot", "Proteína", 60),
            ("lip", "Lípidos", 55),
            ("hc", "H de C", 55),
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
        self.ing_tree.tag_configure(
            "falta_grupo", foreground="#FFFFFF",
            font=("Segoe UI", 8, "italic"),
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

        # --- contenedor con scroll vertical ---
        lienzo = tk.Canvas(right, bg=GRIS_OSCURO, highlightthickness=0)
        barra_lienzo = ttk.Scrollbar(
            right, orient="vertical", command=lienzo.yview
        )
        interior = ttk.Frame(lienzo, style="Gym.TFrame")
        interior.bind(
            "<Configure>",
            lambda _e: lienzo.configure(scrollregion=lienzo.bbox("all")),
        )
        lienzo.create_window((0, 0), window=interior, anchor="nw",
                             tags="marco_int")
        lienzo.configure(yscrollcommand=barra_lienzo.set)
        lienzo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra_lienzo.pack(side=tk.RIGHT, fill=tk.Y)

        def _al_ancho(event):
            lienzo.itemconfigure("marco_int", width=event.width)

        lienzo.bind("<Configure>", _al_ancho)

        def _al_rueda(event):
            try:
                if event.widget.winfo_class() in (
                        "Treeview", "Text", "Combobox", "Listbox", "Spinbox"):
                    return
            except Exception:
                pass
            lienzo.yview_scroll(-1 * int(event.delta / 120), "units")

        lienzo.bind_all("<MouseWheel>", _al_rueda, add="+")

        # --- Aportaciones Totales del día (tarjetas estilo SMAE) ---
        ttk.Label(
            interior, text="APORTACIONES TOTALES DEL DÍA",
            style="Estado.TLabel", font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=(2, 3))
        tarjetas = ttk.Frame(interior, style="Gym.TFrame")
        tarjetas.pack(fill=tk.X, padx=5, pady=(0, 4))
        self.cards_macro = {}
        for clave, etiqueta, bg in (
            ("energia_kcal", "Energía", "#F79B6A"),
            ("proteina_g", "Proteína", "#F1723B"),
            ("lipidos_g", "Lípidos", "#A9CB86"),
            ("hc_g", "H de C", "#4C7A2F"),
        ):
            card = tk.Frame(tarjetas, bg=bg, padx=6, pady=4)
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            tk.Label(
                card, text=etiqueta, bg=bg, fg="#FFFFFF",
                font=("Segoe UI", 7),
            ).pack(anchor=tk.W)
            lbl = tk.Label(
                card, text="0", bg=bg, fg="#FFFFFF",
                font=("Segoe UI", 11, "bold"),
            )
            lbl.pack(anchor=tk.W)
            unidad = "kcal" if clave == "energia_kcal" else "g"
            tk.Label(
                card, text=unidad, bg=bg, fg="#FFFFFF",
                font=("Segoe UI", 7),
            ).pack(anchor=tk.W)
            self.cards_macro[clave] = lbl

        # --- Menú cargado del día (platillos por tiempo) ---
        ttk.Label(
            interior, text="PLATILLOS DEL MENÚ (TIEMPO ACTUAL)",
            style="Estado.TLabel", font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=(4, 2))
        marco_menu = ttk.Frame(interior, style="Gym.TFrame")
        marco_menu.pack(fill=tk.X, padx=5, pady=(0, 4))
        self.menu_tree = ttk.Treeview(
            marco_menu, columns=("eq",), show="tree headings", height=9,
            style="Gym.Treeview", selectmode="none",
        )
        self.menu_tree.heading("#0", text="Tiempo / Platillo / Ingrediente")
        self.menu_tree.column("#0", width=200, anchor=tk.W)
        self.menu_tree.heading("eq", text="Eq.")
        self.menu_tree.column("eq", width=45, anchor=tk.CENTER)
        self.menu_tree.tag_configure(
            "platillo", font=("Segoe UI", 8, "bold"), foreground=NEON)
        self.menu_tree.tag_configure(
            "tiempo_n", font=("Segoe UI", 8, "bold"), foreground=BLANCO)
        bar_menu = ttk.Scrollbar(
            marco_menu, orient=tk.VERTICAL, command=self.menu_tree.yview
        )
        self.menu_tree.configure(yscrollcommand=bar_menu.set)
        self.menu_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        bar_menu.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(
            interior, text="TIEMPO ACTUAL", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.tot_tiempo = {}
        for clave, etiqueta in MICRO_CAMPOS:
            self.tot_tiempo[clave] = self._fila_total(interior, etiqueta, NEON)

        ttk.Separator(interior, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        ttk.Label(
            interior, text="TOTAL DEL DÍA", style="Estado.TLabel",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.tot_dia = {}
        for clave, etiqueta in MICRO_CAMPOS:
            self.tot_dia[clave] = self._fila_total(interior, etiqueta, NEON)

        # --- Equivalencias por grupo del día (formato SMAE) ---
        ttk.Separator(interior, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(
            interior, text="EQUIVALENCIAS POR GRUPO (DÍA)",
            style="Estado.TLabel", font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=(0, 2))
        marco_eq = ttk.Frame(interior, style="Gym.TFrame")
        marco_eq.pack(fill=tk.X, padx=5)
        self.eq_tree = ttk.Treeview(
            marco_eq, columns=("subgrupo", "eq"), show="headings", height=8,
            style="Gym.Treeview", selectmode="none",
        )
        self.eq_tree.heading("subgrupo", text="Subgrupo")
        self.eq_tree.heading("eq", text="Equivalentes")
        self.eq_tree.column("subgrupo", width=130, anchor=tk.W)
        self.eq_tree.column("eq", width=90, anchor=tk.CENTER)
        self.eq_tree.tag_configure(
            "con_eq", font=("Segoe UI", 9, "bold"), foreground="#4C7A2F"
        )
        bar_eq = ttk.Scrollbar(
            marco_eq, orient=tk.VERTICAL, command=self.eq_tree.yview
        )
        self.eq_tree.configure(yscrollcommand=bar_eq.set)
        self.eq_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        bar_eq.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Congruencia: distribución (Equivalentes) vs menú cargado ---
        ttk.Separator(interior, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(
            interior, text="CONGRUENCIA CON LA DISTRIBUCIÓN",
            style="Estado.TLabel", font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=(0, 2))
        marco_cong = ttk.Frame(interior, style="Gym.TFrame")
        marco_cong.pack(fill=tk.X, padx=5)
        cols_cong = ("tiempo", "subgrupo", "distr", "menu", "estado")
        self.cong_tree = ttk.Treeview(
            marco_cong, columns=cols_cong, show="headings", height=10,
            style="Gym.Treeview", selectmode="none",
        )
        for col, texto, ancho, ancla in (
            ("tiempo", "Tiempo", 92, tk.W),
            ("subgrupo", "Subgrupo", 100, tk.W),
            ("distr", "Distrib.", 58, tk.E),
            ("menu", "Menú", 58, tk.E),
            ("estado", "Estado", 84, tk.CENTER),
        ):
            self.cong_tree.heading(col, text=texto)
            self.cong_tree.column(col, width=ancho, anchor=ancla)
        self.cong_tree.tag_configure(
            "falta", foreground="#FF8A80", font=("Segoe UI", 8, "bold"))
        self.cong_tree.tag_configure(
            "sobra", foreground="#7EC8FF")
        self.cong_tree.tag_configure(
            "ok", foreground="#9CCC65", font=("Segoe UI", 8, "bold"))
        self.cong_tree.tag_configure("info", foreground=GRIS_TEXTO)
        bar_cong = ttk.Scrollbar(
            marco_cong, orient=tk.VERTICAL, command=self.cong_tree.yview
        )
        self.cong_tree.configure(yscrollcommand=bar_cong.set)
        self.cong_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        bar_cong.pack(side=tk.RIGHT, fill=tk.Y)

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
        self._parte_activa_idx = None
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
        if getattr(self, "_sync_platillo", False):
            return
        idx = self._tiempo_idx()
        self.datos[self.dia_actual]["platillos"][idx] = self.platillo_var.get()

    def _partes(self, dia, idx):
        """Lista de platillos (partes) del tiempo; la crea si no existe."""
        return self.platillos_partes.setdefault((dia, idx), [])

    def _dividir(self, texto):
        """Separa un nombre combinado 'A + B' en sus partes."""
        return [x.strip() for x in re.split(r"\s+\+\s+", texto or "")
                if x.strip()]

    def _mapear_claves_tiempo(self, mapping, destino_tiempos, tiempos_menu):
        """Mapea las claves de tiempo del detalle guardado a los tiempos
        vigentes (por nombre y, en su defecto, por posición)."""
        resultado = {}
        for k, nombre in (mapping or {}).items():
            try:
                idx_menu = int(k)
            except (TypeError, ValueError):
                continue
            if not nombre:
                continue
            t_obj = None
            if idx_menu < len(tiempos_menu):
                nombre_t = (tiempos_menu[idx_menu] or "").strip().lower()
                t_obj = next((i for i, t in enumerate(destino_tiempos)
                              if (t or "").strip().lower() == nombre_t),
                             None)
            if t_obj is None and idx_menu < len(destino_tiempos):
                t_obj = idx_menu
            if t_obj is not None:
                previo = resultado.get(t_obj)
                if previo and nombre not in previo:
                    resultado[t_obj] = previo + " + " + nombre
                else:
                    resultado[t_obj] = nombre
        return resultado

    def _parte_activa(self):
        idx = self._tiempo_idx()
        partes = self._partes(self.dia_actual, idx)
        i = self._parte_activa_idx
        if i is None or not (0 <= i < len(partes)):
            return None
        return partes[i]

    def _sincronizar_alimentos_de_partes(self, dia, idx):
        """Reconstruye los alimentos del tiempo desde sus platillos (partes)."""
        partes = self._partes(dia, idx)
        self.datos[dia]["alimentos"][idx] = [
            dict(i) for parte in partes for i in parte["ingredientes"]
        ]
        self._refrescar_platillos_menu()

    def _set_platillo_var(self, texto):
        self._sync_platillo = True
        self.platillo_var.set(texto)
        self._sync_platillo = False

    def _render_tiempo(self):
        idx = self._tiempo_idx()
        partes = self._partes(self.dia_actual, idx)
        self._parte_activa_idx = None
        if len(partes) == 1:
            self._parte_activa_idx = 0
        self._reflejar_campos_partes()
        self._refrescar_platillos()
        self._refrescar_platillos_menu()
        self._refrescar_subgrupos()
        self._cargar_ingredientes()
        self._actualizar_restante()

    def _reflejar_campos_partes(self):
        """Coloca en el campo Platillo el nombre de la parte activa. Si el
        tiempo trae nombres combinados «A + B» (o portadores sin grupo),
        los separa en partes con sus ingredientes del catálogo y sincroniza
        los alimentos del tiempo."""
        idx = self._tiempo_idx()
        dia = self.dia_actual
        partes = self._partes(dia, idx)
        if not partes:
            combinado = self.datos[dia]["platillos"].get(idx, "")
            nombres = self._dividir(combinado) if combinado else []
            if nombres:
                nuevas = []
                for nombre in nombres:
                    nuevas.append({
                        "nombre": nombre,
                        "ingredientes": self._ingredientes_de_catalogo(nombre),
                    })
                if any(p["ingredientes"] for p in nuevas):
                    self.platillos_partes[(dia, idx)] = nuevas
                    partes = nuevas
                    lista = self.datos[dia]["alimentos"].get(idx, [])
                    if not any(isinstance(r.get("subgrupo_idx"), int)
                               for r in lista):
                        self._sincronizar_alimentos_de_partes(dia, idx)
        i = self._parte_activa_idx
        activa = partes[i] if i is not None and 0 <= i < len(partes) else None
        if activa is not None:
            texto = activa["nombre"]
        elif len(partes) == 1:
            texto = partes[0]["nombre"]
        elif partes:
            texto = ""
        else:
            texto = self.datos[dia]["platillos"].get(idx, "")
        self._set_platillo_var_en(self.platillo_var, texto)

    def _set_platillo_var_en(self, campo, texto):
        self._sync_platillo = True
        campo.set(texto)
        self._sync_platillo = False

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

        parte = self._parte_activa()
        if parte is not None:
            parte["ingredientes"].append(dict(registro))
            self._sincronizar_alimentos_de_partes(self.dia_actual, idx)
            self._actualizar_menu_dia()
            self._actualizar_congruencia()
        else:
            self.datos[self.dia_actual]["alimentos"].setdefault(
                idx, []).append(registro)
        self._cargar_ingredientes()
        self.alimento_var.set("")
        self._actualizar_restante()

    def _cargar_ingredientes(self):
        for item in self.ing_tree.get_children():
            self.ing_tree.delete(item)
        idx = self._tiempo_idx()
        parte = self._parte_activa()
        marco = getattr(self, "_marco_izq", None)
        if parte is not None:
            lista = parte["ingredientes"]
            if marco is not None:
                marco.configure(text=f"Platillo: {parte['nombre']}")
        else:
            partes = self._partes(self.dia_actual, idx)
            if partes:
                # Hay platillos cargados pero ninguno seleccionado:
                # la tabla queda vacía hasta elegir uno arriba.
                lista = []
                if marco is not None:
                    marco.configure(
                        text="Ingredientes (selecciona un platillo)")
            else:
                lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
                if marco is not None:
                    marco.configure(text="Platillo e ingredientes")
        excesos = self._excesos_idx()
        for i, reg in enumerate(lista):
            sg = reg.get("subgrupo_idx")
            tags = ("exceso",) if sg in excesos else ()
            if isinstance(sg, int) and 0 <= sg < len(SUBGRUPOS_CORTO):
                nombre_grupo = SUBGRUPOS_CORTO[sg]
            else:
                nombre_grupo = reg.get("grupo") or "—"
            self.ing_tree.insert(
                "", tk.END, iid=str(i), tags=tags,
                values=(
                    reg["alimento"],
                    nombre_grupo,
                    f"{reg['eq_cantidad']:g}",
                    f"{(reg.get('energia_kcal') or 0) * reg['eq_cantidad']:.1f}",
                    f"{(reg.get('proteina_g') or 0) * reg['eq_cantidad']:.1f}",
                    f"{(reg.get('lipidos_g') or 0) * reg['eq_cantidad']:.1f}",
                    f"{(reg.get('hc_g') or 0) * reg['eq_cantidad']:.1f}",
                ),
            )
        # Filas de referencia (blancas): grupos que faltan del presupuesto
        # del tiempo y cuántos equivalentes faltan.
        if parte is not None:
            usados = {}
            for reg in self.datos[self.dia_actual]["alimentos"].get(idx, []):
                sg = reg.get("subgrupo_idx")
                if isinstance(sg, int):
                    try:
                        usados[sg] = usados.get(sg, 0.0) + float(
                            reg.get("eq_cantidad") or 0)
                    except (TypeError, ValueError):
                        pass
            for sg, corto in enumerate(SUBGRUPOS_CORTO):
                objetivo = self._presupuesto(idx, sg)
                if objetivo <= 0:
                    continue
                falta = objetivo - usados.get(sg, 0.0)
                if falta > 0.01:
                    self.ing_tree.insert(
                        "", tk.END, iid=f"falta-{sg}",
                        tags=("falta_grupo",),
                        values=(f"Falta: {corto}", "", f"{falta:g}",
                                "", "", "", ""),
                    )
        self._actualizar_totales()

    def _eliminar_ingrediente(self):
        sel = self.ing_tree.selection()
        if not sel:
            messagebox.showwarning("Menús", "Selecciona un ingrediente.")
            return
        idx = self._tiempo_idx()
        parte = self._parte_activa()
        if parte is not None:
            lista = parte["ingredientes"]
        else:
            lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        try:
            pos = int(sel[0])
        except ValueError:
            return  # fila de referencia (grupo faltante), no se elimina
        if 0 <= pos < len(lista):
            lista.pop(pos)
        if parte is not None:
            self._sincronizar_alimentos_de_partes(self.dia_actual, idx)
            self._actualizar_menu_dia()
            self._actualizar_congruencia()
        self._cargar_ingredientes()
        self._actualizar_restante()

    def _limpiar_tiempo(self):
        idx = self._tiempo_idx()
        self.platillos_partes.pop((self.dia_actual, idx), None)
        self._parte_activa_idx = None
        self.datos[self.dia_actual]["alimentos"][idx] = []
        self.datos[self.dia_actual]["platillos"][idx] = ""
        self._reflejar_campos_partes()
        self._refrescar_platillos()
        self._refrescar_platillos_menu()
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
        parte = self._parte_activa()
        if parte is not None:
            lista = parte["ingredientes"]
        else:
            lista = self.datos[self.dia_actual]["alimentos"].get(idx, [])
        try:
            pos = int(sel[0])
        except ValueError:
            return  # fila de referencia (grupo faltante), no es editable
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
        if parte is not None:
            self._sincronizar_alimentos_de_partes(self.dia_actual, idx)
            self._actualizar_menu_dia()
            self._actualizar_congruencia()
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
    def _refrescar_platillos_menu(self):
        """Tabla de los platillos del menú cargado en el tiempo actual."""
        arbol = getattr(self, "platillos_menu_tree", None)
        if arbol is None or not arbol.winfo_exists():
            return
        arbol.delete(*arbol.get_children())
        idx = self._tiempo_idx()
        partes = self._partes(self.dia_actual, idx)
        for i, parte in enumerate(partes):
            eq_total = 0.0
            for reg in parte["ingredientes"]:
                try:
                    eq_total += float(reg.get("eq_cantidad") or 0)
                except (TypeError, ValueError):
                    pass
            arbol.insert("", tk.END, iid=str(i), open=False,
                         text=parte["nombre"],
                         values=(f"{eq_total:g}",))
        if self._parte_activa_idx is not None and \
                0 <= self._parte_activa_idx < len(partes):
            arbol.selection_set(str(self._parte_activa_idx))
            arbol.see(str(self._parte_activa_idx))

    def _on_platillos_menu_select(self, _event=None):
        """Al seleccionar un platillo en la tabla, muestra sus ingredientes
        en la tabla de abajo (editables)."""
        arbol = getattr(self, "platillos_menu_tree", None)
        if arbol is None:
            return
        seleccion = arbol.selection()
        if not seleccion:
            return
        try:
            i = int(seleccion[0])
        except ValueError:
            return
        idx = self._tiempo_idx()
        partes = self._partes(self.dia_actual, idx)
        if 0 <= i < len(partes):
            self._parte_activa_idx = i
            self._cargar_ingredientes()
            self._actualizar_restante()

    def _menu_plat_contextual(self, event):
        """Clic derecho en la tabla de platillos: menú para eliminar."""
        arbol = getattr(self, "platillos_menu_tree", None)
        if arbol is None:
            return
        item = arbol.identify_row(event.y)
        if not item:
            return
        arbol.selection_set(item)
        self._on_platillos_menu_select()
        menu = tk.Menu(arbol, tearoff=0)
        menu.add_command(
            label="🗑 Eliminar platillo del menú",
            command=self._eliminar_platillo_menu,
            font=("Segoe UI", 9),
        )
        menu.add_separator()
        menu.add_command(label="Cancelar")
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _eliminar_platillo_menu(self):
        """Elimina del tiempo actual el platillo seleccionado en la tabla."""
        arbol = getattr(self, "platillos_menu_tree", None)
        if arbol is None:
            return
        seleccion = arbol.selection()
        if not seleccion:
            return
        try:
            i = int(seleccion[0])
        except ValueError:
            return
        idx = self._tiempo_idx()
        partes = self._partes(self.dia_actual, idx)
        if not (0 <= i < len(partes)):
            return
        nombre = partes[i]["nombre"]
        if not messagebox.askyesno(
                "Menús", f"¿Eliminar «{nombre}» del menú de este tiempo?"):
            return
        partes.pop(i)
        if not partes:
            self.platillos_partes.pop((self.dia_actual, idx), None)
        self.datos[self.dia_actual]["platillos"][idx] = " + ".join(
            p["nombre"] for p in partes)
        self._parte_activa_idx = None
        self._sincronizar_alimentos_de_partes(self.dia_actual, idx)
        self._reflejar_campos_partes()
        self._refrescar_platillos()
        self._refrescar_platillos_menu()
        self._cargar_ingredientes()
        self._actualizar_restante()
        self._actualizar_menu_dia()
        self._actualizar_congruencia()

    def _aplicar_texto_menu(self, _event=None):
        """Gestiona el campo Menú: si el texto coincide con un menú guardado
        lo carga; si no, toma el texto como nombre del menú actual (se
        guardará como nuevo con GUARDAR NUEVO)."""
        combo = getattr(self, "menu_smae_combo", None)
        if combo is None:
            return
        texto = (combo.get() or "").strip()
        if not texto:
            return
        if texto in getattr(self, "_combo_menus_map", {}):
            self._cargar_menu_smae()
            return
        self.nombre_menu_actual = texto

    def _nombrar_menu_actual(self, _event=None):
        """Toma el texto escrito en el campo Menú como nombre del menú
        actual (se usa al guardar como plantilla)."""
        combo = getattr(self, "menu_smae_combo", None)
        if combo is None:
            return
        texto = (combo.get() or "").strip()
        if not texto:
            return
        if texto in getattr(self, "_combo_menus_map", {}):
            return  # es un menú guardado de la lista
        self.nombre_menu_actual = texto

    def _refrescar_platillos(self):
        """Puebla el combo de platillos: primero las partes del tiempo actual
        (menús cargados), luego los guardados del catálogo."""
        tiempo = self.tiempo_var.get()
        platillos = database.get_platillos(tiempo) if tiempo else []
        self._platillos_tiempo = {p["nombre"]: p for p in platillos}
        valores = []
        idx = self._tiempo_idx()
        for parte in self._partes(self.dia_actual, idx):
            marcador = f"▸ {parte['nombre']}"
            self._platillos_tiempo[marcador] = {
                "nombre": parte["nombre"],
                "_es_parte": True,
                "ingredientes": json.dumps(parte["ingredientes"],
                                           ensure_ascii=False),
            }
            valores.append(marcador)
        for p in platillos:
            if p["nombre"] not in valores:
                valores.append(p["nombre"])
        self.platillo_combo["values"] = valores

    def _agregar_parte(self, nombre, ingredientes):
        """Agrega (o reemplaza) un platillo como parte del tiempo actual y
        lo deja activo. Permite varios platillos por tiempo de comida."""
        if self.paciente_id is None:
            messagebox.showwarning("Menús", "Selecciona un paciente primero.")
            return
        if not ingredientes:
            messagebox.showwarning(
                "Menús", "El platillo no tiene ingredientes.")
            return
        idx = self._tiempo_idx()
        nombre = (nombre or "").strip()
        partes = self._partes(self.dia_actual, idx)
        if partes:
            reemplazar = messagebox.askyesno(
                "Menús",
                f"El tiempo ya tiene platillos.\n\n"
                f"¿Reemplazarlos por «{nombre}»?\n"
                "(Responde No para agregarlo junto a los existentes)",
            )
        else:
            reemplazar = messagebox.askyesno(
                "Menús",
                "El tiempo actual ya tiene ingredientes sueltos.\n\n"
                "¿Reemplazarlos por los de este platillo?\n"
                "(Responde No para agregarlos a los existentes)",
            )
        if reemplazar:
            partes = []
        else:
            partes = [p for p in partes
                      if p["nombre"].strip().lower() != nombre.lower()]
        partes.append({"nombre": nombre,
                       "ingredientes": [dict(i) for i in ingredientes]})
        self.platillos_partes[(self.dia_actual, idx)] = partes
        self._parte_activa_idx = len(partes) - 1
        self._sincronizar_alimentos_de_partes(self.dia_actual, idx)
        self._reflejar_campos_partes()
        self._refrescar_platillos()
        self._refrescar_platillos_menu()
        self._cargar_ingredientes()
        hijos = self.ing_tree.get_children()
        if hijos:
            self.ing_tree.selection_set(hijos[0])
        self._actualizar_restante()
        self._avisar_subgrupos_platillo()
        self._actualizar_menu_dia()
        self._actualizar_congruencia()

    def _preguntar_categoria(self):
        """Pregunta la categoría del menú (Vegano, Actualidad, etc.).
        Devuelve la categoría elegida o None si se cancela."""
        ventana = tk.Toplevel(self.marco.winfo_toplevel())
        ventana.title("Categoría del menú")
        ventana.configure(bg=GRIS_OSCURO)
        ventana.transient(self.marco.winfo_toplevel())
        ventana.grab_set()
        ventana.resizable(False, False)
        ttk.Label(
            ventana, text="¿A qué categoría pertenece el menú?",
            style="Estado.TLabel",
        ).pack(anchor=tk.W, padx=16, pady=(14, 6))
        var = tk.StringVar(value=CATEGORIAS_MENU[0])
        ttk.Combobox(
            ventana, textvariable=var, values=list(CATEGORIAS_MENU),
            state="readonly", width=24, style="Gym.TCombobox",
        ).pack(anchor=tk.W, padx=16)
        elegida = {"valor": None}

        def aceptar():
            elegida["valor"] = (var.get() or "").strip() or None
            ventana.destroy()

        barra = ttk.Frame(ventana, style="Gym.TFrame")
        barra.pack(fill=tk.X, padx=16, pady=14)
        tk.Button(
            barra, text="GUARDAR", command=aceptar, font=("Impact", 11),
            fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            barra, text="CANCELAR", command=ventana.destroy,
            font=("Impact", 11), fg=NEON, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT)
        ventana.wait_window()
        return elegida["valor"]

    def _guardar_menu_nuevo(self):
        """Guarda el menú actual como NUEVO (no modifica el cargado):
        usa el nombre escrito en el campo Menú y pregunta la categoría
        (Vegano, Actualidad, etc.), que queda en el nombre."""
        categoria = self._preguntar_categoria()
        if categoria is None:
            return
        nombre = (getattr(self, "nombre_menu_actual", None)
                  or (self.menu_smae_combo.get() or "").strip())
        if not nombre.lower().startswith(categoria.lower()):
            nombre = f"{categoria} · {nombre}"
        kcal = self._kcal_promedio_dia()
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
        database.guardar_menu_guardado(
            nombre, round(kcal), json.dumps(datos, ensure_ascii=False)
        )
        self._refrescar_combo_menus_smae()
        for i, valor in enumerate(self.menu_smae_combo["values"]):
            if valor.startswith(nombre):
                self.menu_smae_combo.current(i)
                break
        self.nombre_menu_actual = nombre
        con = database.get_connection()
        try:
            nuevo_id = con.execute(
                "SELECT id_menu_guardado FROM menus_guardados "
                "ORDER BY id_menu_guardado DESC LIMIT 1").fetchone()[0]
            self._menu_actual_id = nuevo_id
        finally:
            con.close()
        messagebox.showinfo(
            "Menús",
            f"Menú guardado como nuevo:\n«{nombre}»\n"
            f"{kcal:.0f} kcal · Categoría: {categoria}")

    def _on_platillo_seleccionado(self, _event=None):
        """Al elegir del combo: si es una parte del tiempo cargado, muestra
        sus ingredientes; si es del catálogo, lo agrega al tiempo."""
        texto = self.platillo_var.get().strip()
        platillo = getattr(self, "_platillos_tiempo", {}).get(texto)
        if not platillo:
            return
        if platillo.get("_es_parte"):
            idx = self._tiempo_idx()
            partes = self._partes(self.dia_actual, idx)
            objetivo = (platillo.get("nombre") or "").strip().lower()
            for i, parte in enumerate(partes):
                if parte["nombre"].strip().lower() == objetivo:
                    self._parte_activa_idx = i
                    self._cargar_ingredientes()
                    self._actualizar_restante()
                    return
        self.cargar_platillo_menu(platillo)

    def cargar_platillo_menu(self, platillo):
        """Agrega (o reemplaza) un platillo como parte del tiempo actual."""
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
        self._agregar_parte(
            (platillo.get("nombre") or "").strip(), ingredientes)

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
                    ["Todos", "Bebidas", "Smoothies"] + tiempos
                )
            except tk.TclError:
                pass
        for p in platillos:
            if filtro == "Bebidas":
                if not _es_bebida(p["nombre"]):
                    continue
            elif filtro == "Smoothies":
                if not _es_smoothie(p["nombre"]):
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
    # Menús guardados (plantillas por kcal)
    # ------------------------------------------------------------------
    def _kcal_promedio_dia(self):
        total = 0.0
        for dia in DIAS_SEMANA:
            for lista in self.datos[dia]["alimentos"].values():
                for reg in lista:
                    total += (reg.get("energia_kcal") or 0) * reg.get(
                        "eq_cantidad", 1.0
                    )
        return total / len(DIAS_SEMANA)

    def _ventana_menus_guardados(self):
        """Ventana con las plantillas de menú: ver, cargar, guardar, eliminar."""
        ventana = tk.Toplevel(self.marco)
        ventana.title("Menús guardados")
        ventana.geometry("1220x620")
        ventana.configure(bg=GRIS_OSCURO)
        self._mg_ventana = ventana

        tk.Label(
            ventana, text="MENÚS GUARDADOS", font=("Impact", 16),
            fg=NEON, bg=GRIS_OSCURO,
        ).pack(fill="x", pady=(6, 2))

        cuerpo = ttk.Frame(ventana, style="Gym.TFrame")
        cuerpo.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        izq = ttk.LabelFrame(cuerpo, text="Plantillas", padding=4)
        izq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        wrap = ttk.Frame(izq, style="Gym.TFrame")
        wrap.pack(fill=tk.BOTH, expand=True)
        cols = ("nombre", "kcal", "creado")
        self._mg_tree = ttk.Treeview(
            wrap, columns=cols, show="headings", height=14,
            selectmode="browse", style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("nombre", "Menú", 190),
            ("kcal", "kcal/día", 70),
            ("creado", "Guardado", 130),
        ):
            self._mg_tree.heading(col, text=texto)
            self._mg_tree.column(col, width=ancho, anchor="center")
        self._mg_tree.column("nombre", anchor="w")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self._mg_tree.yview)
        self._mg_tree.configure(yscrollcommand=sb.set)
        self._mg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._mg_tree.bind(
            "<<TreeviewSelect>>", self._ver_detalle_menu_guardado
        )
        self._mg_tree.bind(
            "<Double-1>", lambda _e: self._cargar_menu_guardado()
        )

        der = ttk.LabelFrame(
            cuerpo, text="Cómo se construye el menú", padding=4
        )
        der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._mg_titulo = tk.Label(
            der, text="Selecciona un menú de la lista",
            font=("Segoe UI", 10, "bold"), fg=NEON, bg=GRIS_OSCURO,
        )
        self._mg_titulo.pack(anchor=tk.W, pady=(0, 2))
        mini = ttk.Frame(der, style="Gym.TFrame")
        mini.pack(fill=tk.X, pady=(0, 2))
        tk.Button(
            mini, text="⤢ EXPANDIR TODO",
            command=lambda: self._mg_constr_toggle(True),
            font=("Segoe UI", 8, "bold"), fg=NEGRO, bg=NEON,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 3))
        tk.Button(
            mini, text="⤡ CONTRAER TODO",
            command=lambda: self._mg_constr_toggle(False),
            font=("Segoe UI", 8, "bold"), fg=BLANCO, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=8, pady=2, cursor="hand2",
        ).pack(side=tk.LEFT)
        det_wrap = ttk.Frame(der, style="Gym.TFrame")
        det_wrap.pack(fill=tk.BOTH, expand=True)
        cols_constr = (
            "alimento", "grupo", "porcion", "eq", "kcal", "prot", "lip", "hc",
        )
        self._mg_constr = ttk.Treeview(
            det_wrap, columns=cols_constr, show="tree headings", height=18,
            selectmode="none", style="Gym.Treeview",
        )
        self._mg_constr.heading("#0", text="Día / Tiempo")
        self._mg_constr.column("#0", width=170, anchor=tk.W)
        for col, texto, ancho, ancla in (
            ("alimento", "Alimento/Platillo", 170, tk.W),
            ("grupo", "Grupo", 95, tk.W),
            ("porcion", "Porción", 62, tk.CENTER),
            ("eq", "Eq.", 40, tk.CENTER),
            ("kcal", "Energía", 58, tk.E),
            ("prot", "Proteína", 58, tk.E),
            ("lip", "Lípidos", 52, tk.E),
            ("hc", "H de C", 52, tk.E),
        ):
            self._mg_constr.heading(col, text=texto)
            self._mg_constr.column(col, width=ancho, anchor=ancla)
        self._mg_constr.tag_configure(
            "dia", font=("Segoe UI", 9, "bold"), foreground=NEON,
        )
        self._mg_constr.tag_configure(
            "tiempo", font=("Segoe UI", 9, "bold"), foreground=BLANCO,
            background=GRIS,
        )
        sb_det = ttk.Scrollbar(
            det_wrap, orient="vertical", command=self._mg_constr.yview
        )
        self._mg_constr.configure(yscrollcommand=sb_det.set)
        self._mg_constr.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_det.pack(side=tk.RIGHT, fill=tk.Y)

        btns = ttk.Frame(ventana, style="Gym.TFrame")
        btns.pack(fill="x", padx=8, pady=6)
        tk.Button(
            btns, text="⬇ CARGAR EN LA SEMANA",
            command=self._cargar_menu_guardado,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btns, text="🖨 IMPRIMIR MENÚ", command=self._imprimir_menu_guardado,
            font=("Impact", 9), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btns, text="💾 GUARDAR MENÚ ACTUAL",
            command=self._guardar_menu_actual,
            font=("Impact", 9), fg=NEGRO, bg=NARANJA, activebackground=NEON,
            activeforeground=NEGRO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btns, text="🗑 ELIMINAR", command=self._eliminar_menu_guardado,
            font=("Impact", 9), fg=NEON, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btns, text="CERRAR", command=ventana.destroy,
            font=("Impact", 9), fg=BLANCO, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=12, pady=4,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=3)

        self._refrescar_arbol_menus_guardados()

    def _refrescar_arbol_menus_guardados(self):
        tree = getattr(self, "_mg_tree", None)
        if tree is None or not tree.winfo_exists():
            return
        for item in tree.get_children():
            tree.delete(item)
        self._mg_catalogo = {}
        for m in database.get_menus_guardados():
            self._mg_catalogo[str(m["id_menu_guardado"])] = m
            tree.insert(
                "", tk.END, iid=str(m["id_menu_guardado"]),
                values=(m["nombre"], f"{m['kcal']}", m.get("creado_en") or ""),
            )
        self._refrescar_combo_menus_smae()

    def _menu_guardado_seleccionado(self):
        tree = getattr(self, "_mg_tree", None)
        if tree is None or not tree.winfo_exists():
            return None
        sel = tree.selection()
        if not sel:
            messagebox.showwarning(
                "Menús guardados", "Selecciona un menú de la lista.",
                parent=self._mg_ventana,
            )
            return None
        return getattr(self, "_mg_catalogo", {}).get(sel[0])

    def _ver_detalle_menu_guardado(self, _event=None):
        """Muestra cómo está construido el menú: día → tiempo → platillo
        → alimentos con grupo, porción, equivalentes y macros."""
        m = self._menu_guardado_seleccionado()
        if not m:
            return
        try:
            datos = json.loads(m.get("detalle") or "{}")
        except (json.JSONDecodeError, TypeError):
            datos = {}
        tiempos = datos.get("tiempos") or []
        dias_datos = datos.get("dias") or {}

        tree = self._mg_constr
        tree.delete(*tree.get_children())
        self._mg_titulo.configure(
            text=f"{m['nombre']}  ·  {m['kcal']} kcal promedio/día"
        )

        def porcion_txt(reg):
            cs, un = reg.get("cantidad_sugerida"), reg.get("unidad") or ""
            texto = " ".join(
                p for p in (f"{cs:g}" if cs else "", un) if p
            )
            return texto or f"{reg.get('eq_cantidad', 0):g}"

        for dia in DIAS_SEMANA:
            info = dias_datos.get(dia)
            if not info:
                continue
            plats = info.get("platillos") or {}
            alimentos = info.get("alimentos") or {}
            if not plats and not alimentos:
                continue

            todos = []
            for lista in alimentos.values():
                todos.extend(lista or [])
            tot_dia = self._sumar(todos)
            nodo_dia = tree.insert(
                "", tk.END, text=dia, open=False, tags=("dia",),
                values=(
                    "", "", "", "",
                    f"{tot_dia['energia_kcal']:.0f}",
                    f"{tot_dia['proteina_g']:.1f}",
                    f"{tot_dia['lipidos_g']:.1f}",
                    f"{tot_dia['hc_g']:.1f}",
                ),
            )
            for idx in range(len(tiempos)):
                lista = alimentos.get(str(idx)) or alimentos.get(idx) or []
                platillo = plats.get(str(idx)) or plats.get(idx) or ""
                if not lista and not platillo:
                    continue
                nombre_t = (
                    tiempos[idx] if idx < len(tiempos) else f"Tiempo {idx + 1}"
                )
                tot_t = self._sumar(lista)
                nodo_t = tree.insert(
                    nodo_dia, tk.END, text=nombre_t, open=False,
                    tags=("tiempo",),
                    values=(
                        platillo or "(sin platillo)", "", "1", "",
                        f"{tot_t['energia_kcal']:.1f}",
                        f"{tot_t['proteina_g']:.1f}",
                        f"{tot_t['lipidos_g']:.1f}",
                        f"{tot_t['hc_g']:.1f}",
                    ),
                )
                for reg in lista:
                    eq = reg.get("eq_cantidad", 1.0) or 1.0
                    tree.insert(
                        nodo_t, tk.END, open=False,
                        values=(
                            reg.get("alimento") or "",
                            reg.get("grupo") or "",
                            porcion_txt(reg),
                            f"{eq:g}",
                            f"{(reg.get('energia_kcal') or 0) * eq:.1f}",
                            f"{(reg.get('proteina_g') or 0) * eq:.1f}",
                            f"{(reg.get('lipidos_g') or 0) * eq:.1f}",
                            f"{(reg.get('hc_g') or 0) * eq:.1f}",
                        ),
                    )
        if not tree.get_children():
            tree.insert("", tk.END, text="(menú vacío)", open=True)

    def _mg_constr_toggle(self, abrir):
        """Expande o contrae todo el árbol de construcción."""
        tree = getattr(self, "_mg_constr", None)
        if tree is None or not tree.winfo_exists():
            return

        def recorrer(item):
            tree.item(item, open=abrir)
            for hijo in tree.get_children(item):
                recorrer(hijo)

        for item in tree.get_children():
            recorrer(item)

    def _imprimir_menu_guardado(self):
        """Genera el PDF con formato SMAE de la plantilla seleccionada."""
        m = self._menu_guardado_seleccionado()
        if not m:
            return
        try:
            datos = json.loads(m.get("detalle") or "{}")
        except (json.JSONDecodeError, TypeError):
            datos = {}
        ruta = menus_print.ruta_temporal_pdf(m["nombre"] or "menu")
        try:
            menus_print.generar_pdf_menus(
                ruta, {}, datos.get("tiempos", []),
                datos.get("dias", {}), subgrupos=SUBGRUPOS_CORTO,
                nombre_menu=m["nombre"],
            )
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}",
                parent=self._mg_ventana,
            )
            return
        try:
            menus_print.abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showerror(
                "Imprimir",
                f"Se generó el PDF en:\n{ruta}\n\n"
                f"No se pudo abrir automáticamente: {error}",
                parent=self._mg_ventana,
            )

    def _cargar_menu_guardado(self, _event=None, m=None, confirmar=True):
        m = m or self._menu_guardado_seleccionado()
        if not m:
            return
        padre = getattr(self, "_mg_ventana", None)
        if confirmar and not messagebox.askyesno(
            "Menús guardados",
            f"¿Reemplazar el menú de la semana actual con «{m['nombre']}»?",
            parent=padre,
        ):
            return
        if self.paciente_id is None:
            messagebox.showwarning(
                "Menús guardados", "Selecciona un paciente primero.",
                parent=padre,
            )
            return
        try:
            datos = json.loads(m.get("detalle") or "{}")
        except (json.JSONDecodeError, TypeError):
            messagebox.showerror(
                "Menús guardados", "La plantilla está dañada.",
                parent=padre,
            )
            return
        # Tiempos: los de la distribución (Equivalentes) si existen;
        # si no, los que traiga la plantilla.
        tab_dist = self._dist_tab()
        nombres_dist = []
        if tab_dist is not None:
            nombres_dist = [v.get() for v in
                            getattr(tab_dist, "dist_nombres_vars", [])]
        if nombres_dist:
            self.tiempos = nombres_dist
        else:
            tiempos = datos.get("tiempos") or []
            if tiempos:
                self.tiempos = tiempos
        destino_tiempos = getattr(self, "tiempos", []) or []
        if destino_tiempos:
            self.tiempo_combo["values"] = destino_tiempos
            if self.tiempo_var.get() not in destino_tiempos:
                self.tiempo_var.set(destino_tiempos[0])
        self.datos = {
            dia: {"platillos": {}, "alimentos": {}} for dia in DIAS_SEMANA
        }
        tiempos_menu = datos.get("tiempos") or []
        for dia in DIAS_SEMANA:
            info = datos.get("dias", {}).get(dia)
            if not info:
                continue
            mapeo = self._mapear_claves_tiempo(
                info.get("platillos"), destino_tiempos, tiempos_menu)
            self.datos[dia]["platillos"].update(mapeo)
        # Cada platillo (o cada parte de un platillo combinado "A + B")
        # se expande a sus ingredientes reales del catálogo; si no está,
        # se conserva lo que traiga la plantilla.
        catalogo = self._catalogo_platillos()
        self._cache_catalogo_plat = None  # refrescar en la próxima lectura
        self.platillos_partes = {}
        self._parte_activa_idx = None
        for dia in DIAS_SEMANA:
            for t_idx, nombre_comb in list(
                    self.datos[dia]["platillos"].items()):
                ings = []
                partes = []
                for parte in [x.strip() for x in re.split(
                        r"\s+\+\s+", nombre_comb or "") if x.strip()]:
                    ing_p = self._ingredientes_de_catalogo(parte, catalogo)
                    if ing_p:
                        partes.append({"nombre": parte,
                                       "ingredientes": [dict(x) for x in ing_p]})
                        ings.extend(ing_p)
                if partes:
                    self.platillos_partes[(dia, t_idx)] = partes
                if not ings:
                    plantilla = self.datos[dia]["alimentos"].get(t_idx, [])
                    # solo ingredientes reales; los registros portadores de
                    # los precargados (subgrupo_idx None) no se muestran
                    ings = [r for r in plantilla
                            if isinstance(r.get("subgrupo_idx"), int)]
                if ings:
                    self.datos[dia]["alimentos"][t_idx] = ings
        self.nombre_menu_actual = m["nombre"]
        self._menu_actual_id = m["id_menu_guardado"]
        self._set_platillo_var_en(self.menu_smae_combo, m["nombre"])
        self._render_tiempo()
        self._actualizar_totales()
        ventana = getattr(self, "_mg_ventana", None)
        if ventana is not None and ventana.winfo_exists():
            ventana.destroy()
        messagebox.showinfo(
            "Menús",
            f"Menú «{m['nombre']}» cargado en la semana.\n"
            "Revísalo por tiempo y presiona GUARDAR MENÚ para asignarlo al "
            "paciente.",
        )

    # ------------------------------------------------------------------
    # Lista desplegable de menús SMAE (sitio + plantillas locales)
    # ------------------------------------------------------------------
    def _refrescar_combo_menus_smae(self):
        combo = getattr(self, "menu_smae_combo", None)
        if combo is None or not combo.winfo_exists():
            return
        self._combo_menus_map = {}
        opciones = []
        for m in database.get_menus_guardados():
            texto = f"{m['nombre']}  ·  {m['kcal']} kcal"
            sufijo = 2
            while texto in self._combo_menus_map:
                texto = f"{m['nombre']} ({sufijo})  ·  {m['kcal']} kcal"
                sufijo += 1
            self._combo_menus_map[texto] = m
            opciones.append(texto)
        combo["values"] = opciones
        if opciones:
            combo.current(0)

    def _menu_smae_seleccionado(self):
        combo = getattr(self, "menu_smae_combo", None)
        if combo is None:
            return None
        texto = combo.get()
        m = getattr(self, "_combo_menus_map", {}).get(texto)
        if not m:
            messagebox.showwarning(
                "Menús SMAE", "Selecciona un menú de la lista desplegable."
            )
        return m

    def _cargar_menu_smae(self, _event=None):
        """Carga directa (sin confirmación) del menú seleccionado."""
        m = self._menu_smae_seleccionado()
        if m:
            self._cargar_menu_guardado(m=m, confirmar=False)

    def _abrir_arbol_menus(self):
        """Esquema de árbol de los menús agrupados por categoría
        (Vegano, Actualidad, Sin Gluten, etc.). Al elegir uno se carga."""
        combo = getattr(self, "menu_smae_combo", None)
        if combo is None:
            return
        ventana = tk.Toplevel(self.marco.winfo_toplevel())
        ventana.title("Menús")
        ventana.configure(bg=GRIS_OSCURO)
        ventana.transient(self.marco.winfo_toplevel())
        ventana.overrideredirect(True)
        x = combo.winfo_rootx()
        y = combo.winfo_rooty() + combo.winfo_height()
        ventana.geometry(f"360x440+{x}+{y}")
        ventana.attributes("-topmost", True)
        marco = ttk.Frame(ventana, style="Gym.TFrame")
        marco.pack(fill=tk.BOTH, expand=True)
        arbol = ttk.Treeview(
            marco, show="tree", style="Gym.Treeview", selectmode="browse"
        )
        barra = ttk.Scrollbar(marco, orient=tk.VERTICAL, command=arbol.yview)
        arbol.configure(yscrollcommand=barra.set)
        arbol.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        barra.pack(side=tk.RIGHT, fill=tk.Y)
        arbol.tag_configure(
            "categoria", font=("Segoe UI", 9, "bold"), foreground=NEON)

        grupos = {}
        for m in database.get_menus_guardados():
            grupos.setdefault(_categoria_de_menu(m["nombre"]), []).append(m)
        categorias = [c for c in CATEGORIAS_MENU if c in grupos] + [
            c for c in sorted(grupos) if c not in CATEGORIAS_MENU]
        for cat in categorias:
            nodo = arbol.insert("", tk.END, text=cat, open=True,
                                tags=("categoria",))
            for m in grupos[cat]:
                arbol.insert(nodo, tk.END, text=m["nombre"],
                             values=(str(m["id_menu_guardado"]),))

        def cerrar(_e=None):
            try:
                ventana.destroy()
            except Exception:
                pass

        def cargar_seleccion(_e=None):
            sel = arbol.selection()
            if not sel:
                return
            valores = arbol.item(sel[0], "values")
            if not valores:
                return  # es una categoría, no un menú
            mid = valores[0]
            fila = next((x for x in database.get_menus_guardados()
                         if str(x["id_menu_guardado"]) == str(mid)), None)
            if fila is not None:
                self._cargar_menu_guardado(m=fila, confirmar=False)
            cerrar()

        arbol.bind("<<TreeviewSelect>>", cargar_seleccion)
        arbol.bind("<Double-1>", cerrar)
        ventana.bind("<Escape>", cerrar)
        ventana.bind("<FocusOut>", cerrar)
        ventana.grab_set()
        arbol.focus_set()

    def _guardar_menu_actual(self):
        if not any(self.datos[d]["alimentos"] for d in DIAS_SEMANA):
            messagebox.showwarning(
                "Menús guardados",
                "El menú de la semana está vacío; arma al menos un tiempo "
                "antes de guardarlo como plantilla.",
                parent=self._mg_ventana,
            )
            return
        kcal = self._kcal_promedio_dia()
        nombre_predeterminado = (getattr(self, "nombre_menu_actual", None)
                                 or f"Menú {kcal:.0f} kcal")
        nombre = simpledialog.askstring(
            "Guardar menú",
            "Nombre de la plantilla:",
            initialvalue=nombre_predeterminado,
            parent=self._mg_ventana,
        )
        if not nombre:
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
        database.guardar_menu_guardado(
            nombre, round(kcal), json.dumps(datos, ensure_ascii=False)
        )
        self._refrescar_arbol_menus_guardados()
        messagebox.showinfo(
            "Menús guardados",
            f"«{nombre}» guardado ({kcal:.0f} kcal promedio/día).",
            parent=self._mg_ventana,
        )

    def _eliminar_menu_guardado(self):
        m = self._menu_guardado_seleccionado()
        if not m:
            return
        if not messagebox.askyesno(
            "Menús guardados", f"¿Eliminar «{m['nombre']}» de las plantillas?",
            parent=self._mg_ventana,
        ):
            return
        database.delete_menu_guardado(m["id_menu_guardado"])
        self._refrescar_arbol_menus_guardados()
        self._mg_constr.delete(*self._mg_constr.get_children())
        self._mg_titulo.configure(text="Selecciona un menú de la lista")

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

        # Tarjetas macro del día (formato SMAE)
        for clave, lbl in self.cards_macro.items():
            lbl.configure(text=f"{tot_dia[clave]:.2f}")

        # Equivalencias por grupo del día
        eqs = self._eq_dia()
        self.eq_tree.delete(*self.eq_tree.get_children())
        for corto, valor in zip(SUBGRUPOS_CORTO, eqs):
            self.eq_tree.insert(
                "", tk.END, values=(corto, f"{valor:g}"),
                tags=("con_eq",) if valor > 0 else (),
            )
        self._actualizar_menu_dia()
        self._actualizar_congruencia()

    def _actualizar_menu_dia(self):
        """Tabla del tiempo actual: platillo → ingredientes."""
        arbol = getattr(self, "menu_tree", None)
        if arbol is None or not arbol.winfo_exists():
            return
        arbol.delete(*arbol.get_children())
        catalogo = self._catalogo_platillos()
        dia = self.dia_actual
        idx = self._tiempo_idx()
        tiempos = getattr(self, "tiempos", []) or []
        tiempo = tiempos[idx] if idx < len(tiempos) else f"Tiempo {idx + 1}"
        nombre_comb = self.datos[dia]["platillos"].get(idx)
        alimentos_t = self.datos[dia]["alimentos"].get(idx, [])
        if not nombre_comb and not alimentos_t:
            arbol.insert("", tk.END, text=f"Sin platillos en {tiempo}.",
                         tags=("info",))
            return
        nodo_t = arbol.insert("", tk.END, text=tiempo, open=True,
                              tags=("tiempo_n",))
        partes_data = self._partes(dia, idx)
        if partes_data:
            for parte in partes_data:
                nodo_p = arbol.insert(
                    nodo_t, tk.END,
                    text="▸ " + parte["nombre"],
                    open=True, tags=("platillo",))
                ings = parte["ingredientes"] or \
                    self._ingredientes_de_catalogo(parte["nombre"])
                for i in ings:
                    arbol.insert(nodo_p, tk.END, open=False,
                                 text=i.get("alimento") or "",
                                 values=(self._fmt_eq(
                                     i.get("eq_cantidad")),))
            return
        partes = [x.strip() for x in re.split(r"\s+\+\s+", nombre_comb)
                  if x.strip()] if nombre_comb else []
        if not partes:
            partes = [None]  # solo alimentos sin platillo
        for parte in partes:
            if parte is None:
                for i in alimentos_t:
                    arbol.insert(nodo_t, tk.END, open=False,
                                 text=i.get("alimento") or "",
                                 values=(self._fmt_eq(
                                     i.get("eq_cantidad")),))
                continue
            nodo_p = arbol.insert(nodo_t, tk.END, text="▸ " + parte,
                                  open=True, tags=("platillo",))
            ings = self._ingredientes_de_catalogo(parte, catalogo) or \
                alimentos_t
            for i in ings:
                arbol.insert(nodo_p, tk.END, open=False,
                             text=i.get("alimento") or "",
                             values=(self._fmt_eq(
                                 i.get("eq_cantidad")),))

    def _fmt_eq(self, valor):
        try:
            return f"{float(valor):.2f}".rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            return "1"

    def _catalogo_platillos(self):
        cache = getattr(self, "_cache_catalogo_plat", None)
        if cache is not None:
            return cache
        catalogo = {}
        try:
            for p in database.get_platillos():
                catalogo[(p.get("nombre") or "").strip().lower()] = p
        except Exception:
            catalogo = {}
        self._cache_catalogo_plat = catalogo
        return catalogo

    def _ingredientes_de_catalogo(self, nombre, catalogo=None):
        catalogo = catalogo if catalogo is not None \
            else self._catalogo_platillos()
        rec = catalogo.get((nombre or "").strip().lower())
        if not rec:
            return []
        try:
            return json.loads(rec.get("ingredientes") or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def _preparacion_lineas(self, nombre, catalogo=None):
        """Líneas de la forma de preparación del platillo (catálogo)."""
        catalogo = catalogo if catalogo is not None \
            else self._catalogo_platillos()
        rec = catalogo.get((nombre or "").strip().lower())
        texto = (rec.get("modo_preparacion") or "") if rec else ""
        lineas = [" ".join(l.split()) for l in texto.splitlines() if l.strip()]
        return lineas or ["(sin preparación registrada)"]

    def _actualizar_congruencia(self):
        """Compara la distribución (Equivalentes) contra el menú cargado:
        por tiempo y subgrupo indica Falta n / Completo / Sobra n."""
        arbol = getattr(self, "cong_tree", None)
        if arbol is None or not arbol.winfo_exists():
            return
        arbol.delete(*arbol.get_children())
        tab = self._dist_tab()
        dist_datos = getattr(tab, "dist_datos", None) if tab else None
        if not dist_datos:
            arbol.insert("", tk.END, tags=("info",),
                         values=("", "Sin distribución definida "
                                 "en Equivalentes", "", "", ""))
            return
        tiempos = getattr(self, "tiempos", []) or []
        alimentos = self.datos[self.dia_actual]["alimentos"]
        filas = 0
        for t_idx, tiempo in enumerate(tiempos):
            por_sub = {}
            for reg in alimentos.get(t_idx, []):
                sg = reg.get("subgrupo_idx")
                if isinstance(sg, int) and 0 <= sg < len(SUBGRUPOS_CORTO):
                    try:
                        eq = float(reg.get("eq_cantidad") or 0)
                    except (TypeError, ValueError):
                        eq = 0.0
                    por_sub[sg] = por_sub.get(sg, 0.0) + eq
            for sg, corto in enumerate(SUBGRUPOS_CORTO):
                objetivo = self._presupuesto(t_idx, sg)
                en_menu = por_sub.get(sg, 0.0)
                if objetivo <= 0 and en_menu <= 0:
                    continue
                dif = objetivo - en_menu
                fmt = lambda x: f"{x:.2f}".rstrip("0").rstrip(".")
                if dif > 0.01:
                    estado, tag = f"Falta {fmt(dif)}", "falta"
                elif dif < -0.01:
                    estado, tag = f"Sobra {fmt(-dif)}", "sobra"
                else:
                    estado, tag = "Completo", "ok"
                arbol.insert("", tk.END, tags=(tag,), values=(
                    tiempo, corto, f"{objetivo:g}", f"{en_menu:g}", estado))
                filas += 1
        if not filas:
            arbol.insert("", tk.END, tags=("info",),
                         values=("", "La distribución y el menú "
                                 "están vacíos", "", "", ""))

    def _eq_dia(self):
        """Equivalentes acumulados por subgrupo en el día actual."""
        eqs = [0.0] * len(SUBGRUPOS)
        for lista in self.datos[self.dia_actual]["alimentos"].values():
            for reg in lista:
                try:
                    eq = float(reg.get("eq_cantidad") or 0)
                except (TypeError, ValueError):
                    eq = 0.0
                idx = reg.get("subgrupo_idx")
                if not isinstance(idx, int):
                    idx = None
                    nombre = (reg.get("grupo") or "").strip().lower()
                    for i, sg in enumerate(SUBGRUPOS):
                        if nombre == sg.lower():
                            idx = i
                            break
                if idx is not None and 0 <= idx < len(eqs):
                    eqs[idx] += eq
        return eqs

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
            elementos = {}
            indices = set(info.get("platillos") or {})
            for t_idx in indices:
                elems = []
                for parte in self._partes(dia, t_idx):
                    if parte.get("ingredientes"):
                        elems.append((parte["nombre"],
                                      parte["ingredientes"]))
                if elems:
                    elementos[t_idx] = elems
            dias[dia] = {
                "platillos": dict(info.get("platillos") or {}),
                "alimentos": dict(info.get("alimentos") or {}),
                "elementos": elementos,
            }

        paciente = database.obtener_paciente(self.paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{self.paciente_id}"
        ruta = menus_print.ruta_temporal_pdf(nombre)
        try:
            menus_print.generar_pdf_menus(
                ruta, paciente, getattr(self, "tiempos", []), dias,
                subgrupos=SUBGRUPOS_CORTO,
                nombre_menu=f"Menú semanal — {nombre}",
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
            "Formato SMAE: tarjetas de aportaciones, equivalentes por grupo, "
            "tablas por tiempo de comida y fichas de platillo.",
        )

    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        registro = database.get_menu(paciente_id)
        self.lbl_estado.configure(text=f"Menús de paciente {paciente_id}")
        self.datos = {
            dia: {"platillos": {}, "alimentos": {}} for dia in DIAS_SEMANA
        }
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
        prep_bar = ttk.Frame(prep, style="Gym.TFrame")
        prep_bar.pack(fill="x", pady=(2, 0))
        boton_voz_prep = tk.Button(
            prep_bar, text="🎙 DICTAR PREPARACIÓN",
            command=lambda: self._dictar_prep(boton_voz_prep),
            font=("Segoe UI", 7, "bold"), fg=NEGRO, bg=NEON,
            activebackground=NARANJA, relief="flat", padx=6,
            cursor="hand2", borderwidth=0,
        )
        boton_voz_prep.pack(side=tk.LEFT)
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

    def _dictar_prep(self, boton):
        """Dicta por voz el modo de preparación del platillo."""
        destino = self.txt_prep

        def recibir(texto, error):
            boton.configure(
                text="🎙 DICTAR PREPARACIÓN", state="normal"
            )
            if error:
                messagebox.showwarning("Voz", error)
                return
            if texto:
                actual = destino.get("1.0", tk.END).rstrip()
                destino.insert("end", (" " if actual else "") + texto)

        ok, mensaje = voz.dictar(recibir, parent=destino)
        if not ok:
            messagebox.showwarning("Voz", mensaje)
            return
        boton.configure(text="🎙 ESCUCHANDO...", state="disabled")

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
