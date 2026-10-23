"""
Pestaña R24h - Recuento de 24 horas por equivalentes SMAE.
Réplica de la lógica de HCEmbarazo (dietosíntesis) integrada al estilo
del proyecto (Nutrición Deportiva).
"""
import tkinter as tk
from tkinter import messagebox, ttk

import database

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

TIEMPOS_COMIDA = [
    "Desayuno",
    "Colación mañana",
    "Almuerzo",
    "Colación tarde",
    "Cena",
    "Colación noche",
]

COL_NUTRIENTES = [
    ("Energía (kcal)", "energia_kcal"),
    ("Proteína (g)", "proteina_g"),
    ("Lípidos (g)", "lipidos_g"),
    ("HC (g)", "hc_g"),
    ("Fibra (g)", "fibra_g"),
    ("Vit. A (µg)", "vitamina_a_ug"),
    ("Vit. C (mg)", "vitamina_c_mg"),
    ("Ác. Fólico (µg)", "acido_folico_ug"),
    ("Hierro (mg)", "hierro_mg"),
    ("Potasio (mg)", "potasio_mg"),
]


class R24hTab:
    def __init__(self, app):
        self.app = app
        self.current_patient_id = None
        self.current_tiempo = TIEMPOS_COMIDA[0]
        self.current_grupo = None
        self.registros = []
        self._search_trace_id = None

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  🍽 R24h  ")

        titulo = tk.Label(
            self.marco,
            text="RECUENTO DE 24 HORAS",
            font=("Impact", 20),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 2))

        self.lbl_estado = ttk.Label(
            self.marco,
            text="R24h: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        paned = ttk.PanedWindow(self.marco, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._crear_panel_alimentos(paned)
        self._crear_panel_registro(paned)
        self._crear_panel_totales(paned)

        self._load_grupos()

    def _crear_panel_alimentos(self, paned):
        left = ttk.LabelFrame(paned, text="Selector de Alimentos (SMAE-5)", padding=5)
        paned.add(left, weight=1)

        search_frame = ttk.Frame(left, style="Gym.TFrame")
        search_frame.pack(fill=tk.X, pady=2)
        ttk.Label(search_frame, text="Buscar:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.search_var = tk.StringVar()
        self._search_trace_id = self.search_var.trace("w", self._on_search)
        ttk.Entry(search_frame, textvariable=self.search_var,
                  style="Gym.TEntry").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2
        )

        group_frame = ttk.Frame(left, style="Gym.TFrame")
        group_frame.pack(fill=tk.X, pady=2)
        ttk.Label(group_frame, text="Grupo:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.grupo_var = tk.StringVar()
        self.grupo_combo = ttk.Combobox(
            group_frame, textvariable=self.grupo_var, state="readonly", width=28,
            style="Gym.TCombobox",
        )
        self.grupo_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.grupo_combo.bind("<<ComboboxSelected>>", self._on_grupo_selected)

        list_frame = ttk.Frame(left, style="Gym.TFrame")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        columnas = ("alimento", "unidad", "cant", "energia")
        self.food_tree = ttk.Treeview(
            list_frame,
            columns=columnas,
            show="headings",
            height=12,
            selectmode="browse",
            style="Gym.Treeview",
        )
        self.food_tree.heading("alimento", text="Alimento")
        self.food_tree.heading("unidad", text="Unidad")
        self.food_tree.heading("cant", text="Cant.")
        self.food_tree.heading("energia", text="Kcal")
        self.food_tree.column("alimento", width=190)
        self.food_tree.column("unidad", width=70)
        self.food_tree.column("cant", width=55)
        self.food_tree.column("energia", width=60)
        vsb = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.food_tree.yview
        )
        self.food_tree.configure(yscrollcommand=vsb.set)
        self.food_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.food_tree.bind("<<TreeviewSelect>>", self._on_food_selected)

        add_frame = ttk.Frame(left, style="Gym.TFrame")
        add_frame.pack(fill=tk.X, pady=3)
        ttk.Label(add_frame, text="Equivalentes:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=2
        )
        self.equiv_var = tk.StringVar(value="1")
        ttk.Spinbox(
            add_frame,
            from_=0.25,
            to=20,
            increment=0.25,
            textvariable=self.equiv_var,
            width=8,
            style="Gym.TSpinbox",
        ).pack(side=tk.LEFT, padx=2)
        self.add_btn = tk.Button(
            add_frame,
            text="+ AGREGAR",
            command=self._add_food,
            font=("Impact", 11),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.add_btn.pack(side=tk.LEFT, padx=6)

    def _crear_panel_registro(self, paned):
        center = ttk.LabelFrame(
            paned, text="Registro por Tiempo de Comida", padding=5
        )
        paned.add(center, weight=2)

        meal_frame = ttk.Frame(center, style="Gym.TFrame")
        meal_frame.pack(fill=tk.X, pady=2)
        self.meal_buttons = []
        for tiempo in TIEMPOS_COMIDA:
            btn = tk.Button(
                meal_frame,
                text=tiempo,
                command=lambda t=tiempo: self._switch_tiempo(t),
                font=("Segoe UI", 8, "bold"),
                fg=BLANCO,
                bg=GRIS,
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=6,
                pady=3,
                cursor="hand2",
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self.meal_buttons.append(btn)

        reg_frame = ttk.Frame(center, style="Gym.TFrame")
        reg_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        reg_cols = ("alimento", "grupo", "equiv", "energia", "proteina", "lipidos", "hc")
        self.reg_tree = ttk.Treeview(
            reg_frame,
            columns=reg_cols,
            show="headings",
            height=10,
            selectmode="browse",
            style="Gym.Treeview",
        )
        for col, texto, ancho in (
            ("alimento", "Alimento", 170),
            ("grupo", "Grupo", 120),
            ("equiv", "Eq.", 45),
            ("energia", "Kcal", 55),
            ("proteina", "Prot", 50),
            ("lipidos", "Lip", 50),
            ("hc", "HC", 50),
        ):
            self.reg_tree.heading(col, text=texto)
            self.reg_tree.column(col, width=ancho)
        reg_vsb = ttk.Scrollbar(
            reg_frame, orient=tk.VERTICAL, command=self.reg_tree.yview
        )
        self.reg_tree.configure(yscrollcommand=reg_vsb.set)
        self.reg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        reg_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(center, style="Gym.TFrame")
        btn_frame.pack(fill=tk.X, pady=2)
        tk.Button(
            btn_frame,
            text="GUARDAR",
            command=self.guardar,
            font=("Impact", 10),
            fg=NEGRO,
            bg=NARANJA,
            activebackground=NEON,
            activeforeground=NEGRO,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=2)
        for texto, comando in (
            ("ELIMINAR SELECCIONADO", self._delete_selected),
            ("LIMPIAR TIEMPO", self._clear_tiempo),
        ):
            tk.Button(
                btn_frame,
                text=texto,
                command=comando,
                font=("Impact", 10),
                fg=NEON,
                bg=GRIS,
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=10,
                pady=4,
                cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)

    def _crear_panel_totales(self, paned):
        right = ttk.LabelFrame(paned, text="Totales", padding=5)
        paned.add(right, weight=1)

        ttk.Label(
            right, text="TIEMPO ACTUAL", style="Estado.TLabel", font=("Segoe UI", 9, "bold")
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.total_labels = {}
        for label, key in COL_NUTRIENTES:
            row = ttk.Frame(right, style="Gym.TFrame")
            row.pack(fill=tk.X, padx=5)
            ttk.Label(row, text=label, style="Gym.TLabel", width=15, anchor=tk.W).pack(
                side=tk.LEFT
            )
            lbl = ttk.Label(
                row, text="0", style="Estado.TLabel", width=10, anchor=tk.E
            )
            lbl.pack(side=tk.RIGHT)
            self.total_labels[key] = lbl

        ttk.Separator(right, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        ttk.Label(
            right, text="TOTAL GENERAL", style="Estado.TLabel", font=("Segoe UI", 9, "bold")
        ).pack(anchor=tk.W, padx=5, pady=2)
        self.total_general_labels = {}
        for label, key in COL_NUTRIENTES:
            row = ttk.Frame(right, style="Gym.TFrame")
            row.pack(fill=tk.X, padx=5)
            ttk.Label(row, text=label, style="Gym.TLabel", width=15, anchor=tk.W).pack(
                side=tk.LEFT
            )
            lbl = tk.Label(
                row, text="0", fg=NEON, bg=GRIS_OSCURO, width=10, anchor=tk.E
            )
            lbl.pack(side=tk.RIGHT)
            self.total_general_labels[key] = lbl

    def cargar(self, paciente_id, paciente=None):
        self.current_patient_id = paciente_id
        nombre = ""
        if paciente:
            nombre = f" — {paciente.get('nombre', '')}"
        self.lbl_estado.configure(text=f"R24h de {paciente_id}{nombre}")
        self._load_registros()

    def limpiar(self):
        self.current_patient_id = None
        self.lbl_estado.configure(text="R24h: sin paciente seleccionado")
        self._load_registros()

    def guardar(self):
        """Confirma el guardado del recuento del tiempo actual."""
        if not self.current_patient_id:
            messagebox.showwarning(
                "R24h", "Selecciona un paciente antes de guardar."
            )
            return
        self._load_registros()
        n = len(self.registros)
        total = sum((r["energia_kcal"] or 0) for r in self.registros)
        messagebox.showinfo(
            "R24h",
            f"Guardado {self.current_tiempo}: {n} alimento(s), "
            f"{total:.1f} kcal.",
        )

    def _load_grupos(self):
        grupos = database.get_smae_grupos()
        names = [g["grupo"] for g in grupos]
        self.grupo_combo["values"] = names
        if names:
            self.grupo_combo.current(0)
            self.current_grupo = names[0]
            self._populate_food_tree(
                database.get_smae_alimentos_por_grupo(names[0])
            )

    def _on_search(self, *args):
        texto = self.search_var.get().strip()
        if len(texto) < 2:
            grupo = self.grupo_var.get()
            if grupo:
                self._populate_food_tree(
                    database.get_smae_alimentos_por_grupo(grupo)
                )
            return
        self._populate_food_tree(database.get_smae_buscar(texto))

    def _on_grupo_selected(self, event=None):
        grupo = self.grupo_var.get()
        if not grupo:
            return
        try:
            self.search_var.trace_vdelete("w", self._search_trace_id)
        except tk.TclError:
            pass
        self.search_var.set("")
        self._search_trace_id = self.search_var.trace("w", self._on_search)
        self.current_grupo = grupo
        self._populate_food_tree(database.get_smae_alimentos_por_grupo(grupo))

    def _populate_food_tree(self, foods):
        for item in self.food_tree.get_children():
            self.food_tree.delete(item)
        for f in foods:
            unidad = f["unidad"] or ""
            cant = f["cantidad_sugerida"] or ""
            kcal = f"{f['energia_kcal']:.0f}" if f["energia_kcal"] else "0"
            self.food_tree.insert(
                "",
                tk.END,
                iid=str(f["id_alimento"]),
                values=(f["alimento"], unidad, cant, kcal),
            )

    def _on_food_selected(self, event=None):
        estado = tk.NORMAL if self.food_tree.selection() else tk.DISABLED
        self.add_btn.configure(state=estado)

    def _add_food(self):
        sel = self.food_tree.selection()
        if not sel or not self.current_patient_id:
            messagebox.showwarning(
                "Advertencia", "Seleccione un alimento y un paciente"
            )
            return
        id_alimento = int(sel[0])
        try:
            equiv = float(self.equiv_var.get())
        except ValueError:
            equiv = 1.0

        alimento = database.get_smae_alimento(id_alimento)
        if not alimento:
            return

        def valor(campo):
            return (alimento.get(campo) or 0) * equiv

        database.insert_r24h(
            {
                "paciente_id": self.current_patient_id,
                "tiempo_comida": self.current_tiempo,
                "id_alimento": id_alimento,
                "alimento": alimento["alimento"],
                "grupo": alimento["grupo"],
                "cantidad_equivalentes": equiv,
                "energia_kcal": valor("energia_kcal"),
                "proteina_g": valor("proteina_g"),
                "lipidos_g": valor("lipidos_g"),
                "hc_g": valor("hc_g"),
                "fibra_g": valor("fibra_g"),
                "vitamina_a_ug": valor("vitamina_a_ug"),
                "vitamina_c_mg": valor("vitamina_c_mg"),
                "acido_folico_ug": valor("acido_folico_ug"),
                "hierro_mg": valor("hierro_mg"),
                "potasio_mg": valor("potasio_mg"),
            }
        )
        self._load_registros()

    def _switch_tiempo(self, tiempo):
        self.current_tiempo = tiempo
        self._load_registros()
        for btn in self.meal_buttons:
            seleccionado = btn.cget("text") == tiempo
            btn.configure(
                bg=NEON if seleccionado else GRIS,
                fg=NEGRO if seleccionado else BLANCO,
            )

    def _load_registros(self):
        for item in self.reg_tree.get_children():
            self.reg_tree.delete(item)
        self.registros = []
        if self.current_patient_id:
            self.registros = database.get_r24h_por_comida(
                self.current_patient_id, self.current_tiempo
            )
        for r in self.registros:
            self.reg_tree.insert(
                "",
                tk.END,
                iid=str(r["id_registro"]),
                values=(
                    r["alimento"],
                    r["grupo"],
                    f"{r['cantidad_equivalentes']:.2f}",
                    f"{r['energia_kcal']:.1f}",
                    f"{r['proteina_g']:.1f}",
                    f"{r['lipidos_g']:.1f}",
                    f"{r['hc_g']:.1f}",
                ),
            )
        self._update_totales()

    def _update_totales(self):
        totals = {key: 0.0 for _, key in COL_NUTRIENTES}
        for r in self.registros:
            for _, key in COL_NUTRIENTES:
                totals[key] += r[key] if r[key] else 0
        for key, val in totals.items():
            self.total_labels[key].configure(text=f"{val:.1f}")

        general = {key: 0.0 for _, key in COL_NUTRIENTES}
        if self.current_patient_id:
            for r in database.get_r24h(self.current_patient_id):
                for _, key in COL_NUTRIENTES:
                    general[key] += r[key] if r[key] else 0
        for key, val in general.items():
            self.total_general_labels[key].configure(text=f"{val:.1f}")

    def _delete_selected(self):
        sel = self.reg_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Advertencia", "Seleccione un registro para eliminar"
            )
            return
        database.delete_r24h(int(sel[0]))
        self._load_registros()

    def _clear_tiempo(self):
        if not self.current_patient_id:
            return
        if messagebox.askyesno(
            "Confirmar", f"¿Limpiar todos los alimentos de {self.current_tiempo}?"
        ):
            for r in database.get_r24h_por_comida(
                self.current_patient_id, self.current_tiempo
            ):
                database.delete_r24h(r["id_registro"])
            self._load_registros()
