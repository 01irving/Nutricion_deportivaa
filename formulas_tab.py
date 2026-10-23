"""
Pestaña Fórmulas predictivas - Cálculo de energía.
Basado en NUTR107x Formula Card (Schofield BMR, PAL) y el Compendio de
Actividades Físicas 2011 (mets.csv) para la energía del ejercicio (EEE).
"""
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

import database

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"


def calcular_edad(fecha_nacimiento, referencia=None):
    """Edad en años (int) a partir de la fecha de nacimiento (texto)."""
    if not fecha_nacimiento:
        return None
    referencia = referencia or date.today()
    texto = str(fecha_nacimiento).strip()
    formatos = (
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
        "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d %H:%M:%S",
    )
    nacimiento = None
    for fmt in formatos:
        try:
            nacimiento = datetime.strptime(texto, fmt).date()
            break
        except ValueError:
            continue
    if nacimiento is None:
        # Intentar tomar solo la fecha si viene con hora/espacio
        solo_fecha = texto.split(" ")[0]
        for fmt in formatos:
            try:
                nacimiento = datetime.strptime(solo_fecha, fmt).date()
                break
            except ValueError:
                continue
    if nacimiento is None:
        return None
    edad = referencia.year - nacimiento.year - (
        (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day)
    )
    return edad if edad >= 0 else None


def bmr_schofield(peso, edad, sexo):
    """BMR Schofield (kcal/día). Devuelve (valor, etiqueta_rango)."""
    if edad < 3:
        valor = (59.512 if sexo == "H" else 58.317) * peso - (
            30.4 if sexo == "H" else 31.1
        )
        return valor, "<3 años"
    if edad < 10:
        valor = (22.706 if sexo == "H" else 20.315) * peso + (
            504.3 if sexo == "H" else 485.9
        )
        return valor, "3-10 años"
    if edad < 18:
        valor = (17.686 if sexo == "H" else 13.384) * peso + (
            658.2 if sexo == "H" else 692.6
        )
        return valor, "10-18 años"
    if edad < 30:
        valor = (15.057 if sexo == "H" else 14.818) * peso + (
            692.2 if sexo == "H" else 486.6
        )
        return valor, "18-30 años"
    if edad < 60:
        valor = (11.472 if sexo == "H" else 8.126) * peso + (
            873.1 if sexo == "H" else 845.6
        )
        return valor, "30-60 años"
    valor = (11.711 if sexo == "H" else 9.082) * peso + (
        587.7 if sexo == "H" else 658.5
    )
    return valor, ">60 años"


class FormulasTab:
    def __init__(self, app):
        self.app = app
        self.tee = None
        self.peso = None
        self.resultado = None

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  ⚡ Fórmulas predictivas  ")

        titulo = tk.Label(
            self.marco,
            text="FÓRMULAS PREDICTIVAS DE ENERGÍA",
            font=("Impact", 20),
            fg=NEON,
            bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 6))

        contenedor = ttk.Frame(self.marco, style="Gym.TFrame")
        contenedor.pack(fill="both", expand=True, padx=8, pady=4)

        # ----- Datos del sujeto -----
        datos = ttk.LabelFrame(contenedor, text="Datos del sujeto", padding=8)
        datos.grid(row=0, column=0, sticky="new", padx=(0, 8))

        self.peso_var = tk.StringVar(value="70")
        self.edad_var = tk.StringVar(value="25")
        self.sexo_var = tk.StringVar(value="H")
        self._campo(datos, 0, "Peso (kg):", self.peso_var)
        self._campo(datos, 1, "Edad (años):", self.edad_var)
        ttk.Label(datos, text="Sexo:", style="Gym.TLabel").grid(
            row=2, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Combobox(
            datos, textvariable=self.sexo_var, values=["H", "M"],
            state="readonly", width=6, style="Gym.TCombobox",
        ).grid(row=2, column=1, sticky="w", padx=4, pady=5)

        self.talla_var = tk.StringVar(value="")
        ttk.Label(datos, text="Talla (cm):", style="Gym.TLabel").grid(
            row=3, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Entry(datos, textvariable=self.talla_var, width=10,
                  style="Gym.TEntry").grid(row=3, column=1, sticky="w", padx=4, pady=5)

        tk.Button(
            datos,
            text="TOMAR DE ANTROPOMETRÍA",
            command=self.cargar_desde_antropometria,
            font=("Impact", 10),
            fg=NEGRO,
            bg=NEON,
            activebackground=NARANJA,
            activeforeground=BLANCO,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
        ).grid(row=4, column=0, columnspan=2, sticky="we", padx=4, pady=(8, 2))

        # ----- Actividad / MET -----
        act = ttk.LabelFrame(
            contenedor, text="Actividad física (Compendio METs)", padding=8
        )
        act.grid(row=1, column=0, sticky="new", padx=(0, 8), pady=(8, 0))

        ttk.Label(act, text="Categoría:", style="Gym.TLabel").grid(
            row=0, column=0, sticky="e", padx=4, pady=5
        )
        self.cat_var = tk.StringVar()
        self.cat_combo = ttk.Combobox(
            act, textvariable=self.cat_var, state="readonly", width=30,
            style="Gym.TCombobox",
        )
        self.cat_combo.grid(row=0, column=1, columnspan=3, sticky="w", padx=4, pady=5)
        self.cat_combo.bind("<<ComboboxSelected>>", self._on_categoria)

        ttk.Label(act, text="Actividad:", style="Gym.TLabel").grid(
            row=1, column=0, sticky="e", padx=4, pady=5
        )
        self.act_var = tk.StringVar()
        self.act_combo = ttk.Combobox(
            act, textvariable=self.act_var, state="readonly", width=52,
            style="Gym.TCombobox",
        )
        self.act_combo.grid(row=1, column=1, columnspan=3, sticky="w", padx=4, pady=5)
        self.act_combo.bind("<<ComboboxSelected>>", self._on_actividad)

        ttk.Label(act, text="METs:", style="Gym.TLabel").grid(
            row=2, column=0, sticky="e", padx=4, pady=5
        )
        self.mets_var = tk.StringVar(value="")
        self.mets_entry = ttk.Entry(act, textvariable=self.mets_var, width=8,
                                    style="Gym.TEntry")
        self.mets_entry.grid(row=2, column=1, sticky="w", padx=4, pady=5)

        ttk.Label(act, text="Horas de ejercicio (h):", style="Gym.TLabel").grid(
            row=2, column=2, sticky="e", padx=4, pady=5
        )
        self.horas_var = tk.StringVar(value="1")
        ttk.Entry(act, textvariable=self.horas_var, width=8,
                  style="Gym.TEntry").grid(
            row=2, column=3, sticky="w", padx=4, pady=5
        )

        # ----- PAL / actividad diaria -----
        pal = ttk.LabelFrame(
            contenedor, text="Actividad diaria (GEE = BMR x PAL x h/24)", padding=8
        )
        pal.grid(row=2, column=0, sticky="new", padx=(0, 8), pady=(8, 0))

        ttk.Label(pal, text="Nivel PAL:", style="Gym.TLabel").grid(
            row=0, column=0, sticky="e", padx=4, pady=5
        )
        self.pal_var = tk.StringVar(value="1.6")
        self.pal_combo = ttk.Combobox(
            pal,
            textvariable=self.pal_var,
            values=[
                "Sedentario (<1.6)",
                "Moderadamente activo (1.6-2.0)",
                "Intensamente activo (>2.0)",
                "Reposo (1.2)",
            ],
            state="readonly",
            width=28,
            style="Gym.TCombobox",
        )
        self.pal_combo.grid(row=0, column=1, sticky="w", padx=4, pady=5)
        self.pal_combo.bind("<<ComboboxSelected>>", self._on_pal)

        ttk.Label(pal, text="PAL manual:", style="Gym.TLabel").grid(
            row=1, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Entry(pal, textvariable=self.pal_var, width=10,
                  style="Gym.TEntry").grid(
            row=1, column=1, sticky="w", padx=4, pady=5
        )

        ttk.Label(pal, text="Horas NO ejercicio (h/24):", style="Gym.TLabel").grid(
            row=2, column=0, sticky="e", padx=4, pady=5
        )
        self.h24_var = tk.StringVar(value="23")
        ttk.Entry(pal, textvariable=self.h24_var, width=10,
                  style="Gym.TEntry").grid(
            row=2, column=1, sticky="w", padx=4, pady=5
        )

        # ----- Botones -----
        barra = ttk.Frame(contenedor, style="Gym.TFrame")
        barra.grid(row=3, column=0, sticky="w", pady=(10, 0))
        botones = [
            ("CALCULAR", self.calcular, True),
            ("GUARDAR", self.guardar, False),
            ("LIMPIAR", self.limpiar, False),
        ]
        for texto, comando, primario in botones:
            tk.Button(
                barra,
                text=texto,
                command=comando,
                font=("Impact", 12),
                fg=NEGRO if primario else NEON,
                bg=NEON if primario else GRIS,
                activebackground=NARANJA,
                activeforeground=BLANCO,
                relief="flat",
                padx=16,
                pady=6,
                cursor="hand2",
            ).pack(side="left", padx=(0, 8))

        # ----- Resultados -----
        res = ttk.LabelFrame(contenedor, text="Resultados", padding=8)
        res.grid(row=0, column=1, rowspan=4, sticky="nsew", padx=(8, 0))
        contenedor.columnconfigure(1, weight=1)
        self.res_labels = {}
        filas = [
            ("bmr", "BMR (Schofield)"),
            ("rango", "Rango de edad"),
            ("gee", "GEE (BMR x PAL x h/24)"),
            ("eee", "EEE (MET x peso x h)"),
            ("tee", "TEE (GEE + EEE)"),
            ("ea", "EA (EI - EEE)"),
        ]
        for i, (clave, etiqueta) in enumerate(filas):
            ttk.Label(res, text=f"{etiqueta}:", style="Gym.TLabel").grid(
                row=i, column=0, sticky="w", padx=4, pady=4
            )
            lbl = tk.Label(res, text="—", fg=NEON, bg=GRIS_OSCURO,
                           font=("Segoe UI", 11, "bold"))
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=4)
            self.res_labels[clave] = lbl

        self._cargar_categorias()

    def _campo(self, parent, fila, etiqueta, var):
        ttk.Label(parent, text=etiqueta, style="Gym.TLabel").grid(
            row=fila, column=0, sticky="e", padx=4, pady=5
        )
        ttk.Entry(parent, textvariable=var, width=10, style="Gym.TEntry").grid(
            row=fila, column=1, sticky="w", padx=4, pady=5
        )

    def _cargar_categorias(self):
        categorias = database.get_mets_categorias()
        self.cat_combo["values"] = categorias
        if categorias:
            self.cat_combo.current(0)
            self._on_categoria()

    def cargar_desde_antropometria(self):
        """Toma peso y talla de antropometría y calcula la edad por fecha de nacimiento.

        Si falta algún dato, deja el campo vacío y muestra el aviso correspondiente.
        """
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            messagebox.showwarning(
                "Fórmulas predictivas",
                "Selecciona un paciente antes de tomar datos.",
            )
            return

        avisos = []

        # --- Peso y talla desde la antropometría más reciente ---
        filas = database.obtener_antropometria()
        fila = next(
            (f for f in filas if f["paciente_id"] == paciente_id), None
        )

        peso_texto = ""
        talla_texto = ""
        if fila is None:
            avisos.append("El paciente no tiene antropometría guardada.")
        else:
            peso_texto = str(fila["peso"] or "").strip().replace(",", ".")
            talla_texto = str(fila["altura"] or "").strip().replace(",", ".")
            if not peso_texto:
                avisos.append("La antropometría no tiene peso.")
            if not talla_texto:
                avisos.append("La antropometría no tiene talla.")

        try:
            self.peso_var.set(f"{float(peso_texto):g}")
        except ValueError:
            self.peso_var.set("")
            if peso_texto:
                avisos.append("El peso guardado no es válido.")

        try:
            self.talla_var.set(f"{float(talla_texto):g}")
        except ValueError:
            self.talla_var.set("")
            if talla_texto:
                avisos.append("La talla guardada no es válida.")

        # --- Edad desde la fecha de nacimiento del paciente ---
        paciente = database.obtener_paciente(paciente_id) or {}
        fecha_nac = paciente.get("fecha_nacimiento") or paciente.get("dob")
        edad = calcular_edad(fecha_nac)
        if edad is not None:
            self.edad_var.set(str(edad))
        else:
            self.edad_var.set("")
            avisos.append("No se pudo calcular la edad (fecha de nacimiento).")

        if avisos:
            messagebox.showinfo("Fórmulas predictivas", "\n".join(avisos))
        else:
            messagebox.showinfo(
                "Fórmulas predictivas",
                "Peso, talla y edad tomados correctamente.",
            )

    def _on_categoria(self, event=None):
        categoria = self.cat_var.get()
        actividades = database.get_mets_por_categoria(categoria)
        etiquetas = [
            f"{a['codigo']}  {a['mets']:.1f}  {a['actividad']}"
            for a in actividades
        ]
        self.act_combo["values"] = etiquetas
        self._actividades = {e: a for e, a in zip(etiquetas, actividades)}
        if etiquetas:
            self.act_combo.current(0)
            self._on_actividad()

    def _on_actividad(self, event=None):
        elegido = self._actividades.get(self.act_var.get())
        if elegido:
            self.mets_var.set(f"{elegido['mets']:.1f}")

    def _on_pal(self, event=None):
        texto = self.pal_var.get()
        valores = {
            "Sedentario (<1.6)": "1.5",
            "Moderadamente activo (1.6-2.0)": "1.7",
            "Intensamente activo (>2.0)": "2.1",
            "Reposo (1.2)": "1.2",
        }
        if texto in valores:
            self.pal_var.set(valores[texto])

    def _float(self, var, nombre):
        try:
            return float(str(var.get()).replace(",", "."))
        except ValueError:
            raise ValueError(f"{nombre} debe ser un número.")

    def calcular(self):
        try:
            peso = self._float(self.peso_var, "Peso")
            edad = self._float(self.edad_var, "Edad")
            met = self._float(self.mets_var, "METs")
            horas = self._float(self.horas_var, "Horas de ejercicio")
            pal = self._float(self.pal_var, "PAL")
            h24 = self._float(self.h24_var, "Horas NO ejercicio")
        except ValueError as error:
            messagebox.showwarning("Validación", str(error))
            return

        bmr, rango = bmr_schofield(peso, edad, self.sexo_var.get())
        gee = bmr * pal * (h24 / 24.0)
        eee = met * peso * horas
        tee = gee + eee
        ea = tee - eee

        self.tee = tee
        self.peso = peso
        self.resultado = {
            "peso": peso,
            "edad": edad,
            "sexo": self.sexo_var.get(),
            "pal": pal,
            "horas_no_ejercicio": h24,
            "categoria": self.cat_var.get(),
            "actividad": self.act_var.get(),
            "mets": met,
            "horas_ejercicio": horas,
            "bmr": bmr,
            "rango_edad": rango,
            "gee": gee,
            "eee": eee,
            "tee": tee,
            "ea": ea,
        }

        self.res_labels["bmr"].configure(text=f"{bmr:.0f} kcal/día")
        self.res_labels["rango"].configure(text=rango)
        self.res_labels["gee"].configure(text=f"{gee:.0f} kcal")
        self.res_labels["eee"].configure(text=f"{eee:.0f} kcal")
        self.res_labels["tee"].configure(text=f"{tee:.0f} kcal/día")
        self.res_labels["ea"].configure(text=f"{ea:.0f} kcal")

    def limpiar(self):
        self.tee = None
        self.peso = None
        self.resultado = None
        for lbl in self.res_labels.values():
            lbl.configure(text="—")

    def guardar(self):
        if getattr(self, "resultado", None) is None:
            messagebox.showwarning(
                "Fórmulas predictivas",
                "Primero calcula los resultados antes de guardar.",
            )
            return
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        if paciente_id is None:
            messagebox.showwarning(
                "Fórmulas predictivas",
                "Selecciona un paciente antes de guardar.",
            )
            return
        datos = dict(self.resultado, paciente_id=paciente_id)
        database.insert_formulas(datos)
        messagebox.showinfo(
            "Fórmulas predictivas",
            "Cálculo guardado para el paciente activo.",
        )
