"""
Pestaña Antecedentes - Antecedentes patológicos y no patológicos.

Estructurado según la Historia Clínica Nutricional:
  - Antecedentes patológicos: familiares, personales, quirúrgicos
  - Antecedentes no patológicos: hábitos (tabaco, alcohol, drogas, café),
    medicamentos, actividad física y problemas intestinales
"""
import tkinter as tk
from tkinter import messagebox, ttk

import antecedentes_print
import database
from antecedentes_defs import (
    ETIQUETA_HABITOS,
    HABITOS_OPCIONES,
    SECCION_NOPATOLOGICOS_HABITOS,
    SECCION_NOPATOLOGICOS_TEXTO,
    SECCION_PATOLOGICOS,
)

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

# (clave, etiqueta, alto_en_caracteres)
CAMPOS_PATOLOGICOS = [
    ("pat_familiares", "Antecedentes familiares", 6),
    ("pat_personales", "Antecedentes personales", 5),
    ("pat_alergia_alimentaria", "Alergia alimentaria", 4),
    ("pat_quirurgicos", "Antecedentes quirúrgicos", 5),
]

CAMPOS_NOPATOLOGICOS_TEXTO = [
    ("nopat_medicamentos", "Medicamentos", 4),
    ("nopat_actividad_fisica", "Actividad física", 4),
    ("nopat_problemas_intestinales", "Problemas intestinales", 4),
]


class AntecedentesTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self.textos = {}
        self.habitos = {}

    # ------------------------------------------------------------------
    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  📋 Antecedentes  ")

        titulo = tk.Label(
            self.marco,
            text="ANTECEDENTES CLÍNICOS",
            font=("Impact", 20), fg=NEON, bg=GRIS_OSCURO,
        )
        titulo.pack(fill="x", pady=(4, 2))

        self.lbl_estado = ttk.Label(
            self.marco, text="Antecedentes: sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        paned = ttk.PanedWindow(self.marco, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._crear_panel_patologicos(paned)
        self._crear_panel_nopatologicos(paned)

    # ------------------------------------------------------------------
    def _crear_panel_patologicos(self, paned):
        left = ttk.LabelFrame(
            paned, text="ANTECEDENTES PATOLÓGICOS", padding=5
        )
        paned.add(left, weight=1)

        ttk.Label(
            left,
            text="Enfermedades y antecedentes con patología",
            style="Estado.TLabel", font=("Segoe UI", 8),
        ).pack(anchor=tk.W, padx=4, pady=(0, 4))

        for clave, etiqueta, alto in CAMPOS_PATOLOGICOS:
            self._crear_area_texto(left, clave, etiqueta, alto)

    def _crear_panel_nopatologicos(self, paned):
        right = ttk.LabelFrame(
            paned, text="ANTECEDENTES NO PATOLÓGICOS", padding=5
        )
        paned.add(right, weight=1)

        ttk.Label(
            right,
            text="Hábitos, medicación y función digestiva",
            style="Estado.TLabel", font=("Segoe UI", 8),
        ).pack(anchor=tk.W, padx=4, pady=(0, 4))

        # --- Hábitos ---
        ttk.Label(right, text="HÁBITOS", style="Gym.TLabel").pack(
            anchor=tk.W, padx=4, pady=(4, 2)
        )
        marco_habitos = ttk.Frame(right, style="Gym.TFrame")
        marco_habitos.pack(fill="x", padx=2)
        fila = 0
        for clave, etiqueta in SECCION_NOPATOLOGICOS_HABITOS:
            opciones = HABITOS_OPCIONES[clave]
            ttk.Label(
                marco_habitos, text=ETIQUETA_HABITOS[clave], style="Gym.TLabel"
            ).grid(row=fila, column=0, sticky="e", padx=4, pady=3)
            var = tk.StringVar()
            ttk.Combobox(
                marco_habitos, textvariable=var, values=opciones,
                state="normal", style="Gym.TCombobox", width=22,
            ).grid(row=fila, column=1, sticky="we", padx=4, pady=3)
            self.habitos[clave] = var
            fila += 1
        marco_habitos.columnconfigure(1, weight=1)

        # --- Campos de texto ---
        for clave, etiqueta, alto in CAMPOS_NOPATOLOGICOS_TEXTO:
            self._crear_area_texto(right, clave, etiqueta, alto)

        # --- Acciones ---
        barra = ttk.Frame(right, style="Gym.TFrame")
        barra.pack(fill="x", pady=(8, 0))
        for texto, cmd in (
            ("GUARDAR", self.guardar),
            ("IMPRIMIR", self.imprimir),
            ("LIMPIAR", self.limpiar),
        ):
            es_guardar = texto == "GUARDAR"
            es_imprimir = texto == "IMPRIMIR"
            if es_guardar:
                fg, bg, act_bg, act_fg = NEGRO, NARANJA, NEON, NEGRO
            elif es_imprimir:
                fg, bg, act_bg, act_fg = NEGRO, NEON, NARANJA, BLANCO
            else:
                fg, bg, act_bg, act_fg = NEON, GRIS, NARANJA, BLANCO
            tk.Button(
                barra, text=texto, command=cmd, font=("Impact", 11),
                fg=fg, bg=bg, activebackground=act_bg, activeforeground=act_fg,
                relief="flat", padx=16, pady=5, cursor="hand2",
            ).pack(side="left", padx=2)

    def _crear_area_texto(self, parent, clave, etiqueta, alto):
        marco = ttk.Frame(parent, style="Gym.TFrame")
        marco.pack(fill="both", expand=True, padx=2, pady=3)
        ttk.Label(marco, text=f"{etiqueta}:", style="Gym.TLabel").pack(
            anchor=tk.W, pady=(0, 2)
        )
        texto = tk.Text(
            marco, height=alto, wrap=tk.WORD, bg=GRIS_OSCURO, fg=BLANCO,
            insertbackground=NEON, relief="flat", padx=6, pady=4,
            font=("Segoe UI", 9),
        )
        texto.pack(fill="both", expand=True)
        self.textos[clave] = texto

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def _leer(self):
        datos = {}
        for clave, texto in self.textos.items():
            datos[clave] = texto.get("1.0", tk.END).strip()
        for clave, var in self.habitos.items():
            datos[clave] = var.get().strip()
        return datos

    def _escribir(self, datos):
        for clave, texto in self.textos.items():
            texto.delete("1.0", tk.END)
            valor = datos.get(clave) or ""
            if valor:
                texto.insert("1.0", valor)
        for clave, var in self.habitos.items():
            var.set(datos.get(clave) or "")

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def guardar(self):
        if self.paciente_id is None:
            messagebox.showwarning(
                "Antecedentes", "Selecciona un paciente antes de guardar."
            )
            return
        try:
            database.guardar_antecedentes(self.paciente_id, self._leer())
        except Exception as error:
            messagebox.showerror(
                "Antecedentes", f"No se pudo guardar:\n{error}"
            )
            return
        messagebox.showinfo(
            "Antecedentes",
            "Antecedentes patológicos y no patológicos guardados.",
        )

    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        registro = database.get_antecedentes(paciente_id) or {}
        self._escribir(registro)
        self.lbl_estado.configure(text=f"Antecedentes de paciente {paciente_id}")

    def imprimir(self):
        """Genera el PDF de la historia de antecedentes y lo abre."""
        if self.paciente_id is None:
            messagebox.showwarning(
                "Antecedentes", "Selecciona un paciente antes de imprimir."
            )
            return

        paciente = database.obtener_paciente(self.paciente_id) or {}
        nombre = paciente.get("nombre") or f"paciente_{self.paciente_id}"
        ruta = antecedentes_print.ruta_temporal_pdf(nombre)
        try:
            antecedentes_print.generar_pdf_antecedentes(
                ruta, paciente, self._leer()
            )
        except Exception as error:
            messagebox.showerror(
                "Imprimir", f"No se pudo generar el reporte:\n{error}"
            )
            return

        try:
            antecedentes_print.abrir_para_imprimir(ruta)
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

    def limpiar(self):
        self._escribir({})
        self.lbl_estado.configure(text="Antecedentes: sin paciente seleccionado")

    def desvincular(self):
        self.paciente_id = None
        self.limpiar()
