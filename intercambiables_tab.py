"""
Pestaña Alimentos intercambiables — opciones de canje por subgrupo.

Muestra los subgrupos que el paciente activo tiene asignados en su
distribución (pestaña Equivalentes), lista los alimentos del SMAE de cada
subgrupo (nombre, cantidad, unidad y peso) y genera un PDF con las
opciones seleccionadas para que el paciente visualice sus canjes.
"""
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import database
from impresion_utils import crear_membrete
from menu_tab import SUBGRUPOS, SUBGRUPOS_CORTO
from menus_print import abrir_para_imprimir

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

NEGRO = "#121212"
GRIS_OSCURO = "#1E1E1E"
GRIS = "#2C2C2C"
NEON = "#C6FF00"
NARANJA = "#FF6D00"
BLANCO = "#F5F5F5"
GRIS_TEXTO = "#B0B0B0"

VINO = colors.HexColor("#BE6E77")
ROSA_HEADER = colors.HexColor("#E7B6BC")
ROSA_FILA = colors.HexColor("#F9ECEE")
GRIS_TABLA = colors.HexColor("#D9A0A8")


def _escapar(texto):
    if texto is None:
        return ""
    return (str(texto).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def _estilos():
    return {
        "banner": ParagraphStyle(
            "banner", fontName="Helvetica-Bold", fontSize=14, leading=18,
            textColor=colors.white),
        "info": ParagraphStyle(
            "info", fontName="Helvetica", fontSize=8.5, leading=11,
            textColor=colors.HexColor("#8A8A8A")),
        "seccion": ParagraphStyle(
            "seccion", fontName="Helvetica-Bold", fontSize=11.5,
            leading=14, textColor=colors.HexColor("#121212"),
            spaceBefore=8, spaceAfter=3, keepWithNext=1),
        "thead": ParagraphStyle(
            "thead", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
            textColor=colors.HexColor("#121212")),
        "celda": ParagraphStyle(
            "celda", fontName="Helvetica", fontSize=8.5, leading=11,
            textColor=colors.HexColor("#121212")),
        "celda_r": ParagraphStyle(
            "celda_r", fontName="Helvetica", fontSize=8.5, leading=11,
            textColor=colors.HexColor("#121212"), alignment=2),
        "nota": ParagraphStyle(
            "nota", fontName="Helvetica-Oblique", fontSize=8, leading=10,
            textColor=colors.HexColor("#8A8A8A")),
    }


def _franja(texto, estilos):
    tabla = Table(
        [[Paragraph(_escapar(texto), estilos["banner"])]],
        colWidths=[7.3 * inch], hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VINO),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return tabla


def generar_pdf_intercambiables(ruta, paciente, dia, secciones,
                                momento=None):
    """Genera el PDF de alimentos intercambiables.

    secciones: [(subgrupo_corto, equivalentes, [registros]), ...]
    """
    estilos = _estilos()
    momento = momento or datetime.now()
    nombre = (paciente.get("nombre") or "").strip() or "Paciente"

    doc = SimpleDocTemplate(
        ruta, pagesize=letter,
        rightMargin=0.6 * inch, leftMargin=0.6 * inch,
        topMargin=0.55 * inch, bottomMargin=0.65 * inch,
        title=f"Alimentos intercambiables — {nombre}",
        author="Nutrición Deportiva",
    )
    flujo = list(crear_membrete()) + [
        _franja(f"Alimentos intercambiables — {nombre}", estilos),
        Spacer(1, 4),
        Paragraph(
            f"Paciente: {_escapar(nombre)} · Distribución del día: "
            f"{_escapar(dia)} · Fecha de impresión: "
            f"{momento.strftime('%d/%m/%Y %H:%M')}", estilos["info"]),
        Spacer(1, 8),
    ]

    for corto, eq, registros in secciones:
        flujo.append(Paragraph(
            f"{_escapar(corto)} — {eq:g} equivalentes", estilos["seccion"]))
        encabezados = ["Alimento", "Cantidad", "Unidad", "Peso neto (g)",
                       "Peso bruto (g)"]
        filas = [[Paragraph(t, estilos["thead"]) for t in encabezados]]
        for reg in registros:
            cs = reg.get("cantidad_sugerida") or 0
            filas.append([
                Paragraph(_escapar(reg.get("alimento") or ""),
                          estilos["celda"]),
                Paragraph(f"{cs:g}" if cs else "—", estilos["celda_r"]),
                Paragraph(_escapar(reg.get("unidad") or "—"),
                          estilos["celda"]),
                Paragraph(f"{reg.get('peso_neto_g') or 0:g}",
                          estilos["celda_r"]),
                Paragraph(f"{reg.get('peso_bruto_g') or 0:g}",
                          estilos["celda_r"]),
            ])
        tabla = Table(filas, colWidths=[
            2.9 * inch, 0.8 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch],
            repeatRows=1, hAlign="LEFT")
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ROSA_HEADER),
            ("GRID", (0, 0), (-1, -1), 0.4, GRIS_TABLA),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, ROSA_FILA]),
        ]))
        flujo.append(tabla)
        flujo.append(Spacer(1, 10))

    flujo.append(Paragraph(
        "Los alimentos de cada subgrupo son intercambiables entre sí: "
        "puedes sustituirlos manteniendo los equivalentes asignados.",
        estilos["nota"]))
    doc.build(flujo)
    return ruta


class IntercambiablesTab:
    def __init__(self, app):
        self.app = app
        self.paciente_id = None
        self._alimentos_actual = []
        self.seleccion = {}  # {sg_idx: [registros]}

    def create(self, parent):
        self.marco = ttk.Frame(parent, style="Gym.TFrame")
        parent.add(self.marco, text="  🥑 Alimentos intercambiables  ")
        self._pestana = self.marco

        tk.Label(
            self.marco, text="ALIMENTOS INTERCAMBIABLES",
            font=("Impact", 20), fg=NEON, bg=GRIS_OSCURO,
        ).pack(fill="x", pady=(4, 2))

        self.lbl_estado = ttk.Label(
            self.marco, text="Sin paciente seleccionado",
            style="Estado.TLabel",
        )
        self.lbl_estado.pack(anchor="w", padx=8, pady=(0, 4))

        barra = ttk.Frame(self.marco, style="Gym.TFrame")
        barra.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Label(barra, text="Día:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(0, 4))
        self.dia_var = tk.StringVar()
        self.dia_combo = ttk.Combobox(
            barra, textvariable=self.dia_var, state="readonly", width=14,
            style="Gym.TCombobox",
        )
        self.dia_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.dia_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._refrescar_subgrupos())
        tk.Button(
            barra, text="📄 GENERAR PDF", command=self.generar_pdf,
            font=("Impact", 10), fg=NEGRO, bg=NARANJA,
            activebackground=NEON, activeforeground=BLANCO,
            relief="flat", padx=12, pady=4, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=2)
        tk.Button(
            barra, text="🧹 LIMPIAR LISTA", command=self.limpiar_lista,
            font=("Impact", 10), fg=NEON, bg=GRIS,
            activebackground=NARANJA, activeforeground=BLANCO,
            relief="flat", padx=10, pady=4, cursor="hand2",
        ).pack(side=tk.RIGHT, padx=2)

        columnas = ttk.Frame(self.marco, style="Gym.TFrame")
        columnas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- 1) Subgrupos asignados al paciente ---
        izq = ttk.LabelFrame(
            columnas, text="Subgrupos asignados (distribución)", padding=4)
        izq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.sg_tree = ttk.Treeview(
            izq, columns=("eq",), show="tree headings", height=16,
            style="Gym.Treeview", selectmode="browse",
        )
        self.sg_tree.heading("#0", text="Subgrupo")
        self.sg_tree.column("#0", width=150, anchor=tk.W)
        self.sg_tree.heading("eq", text="Eq/día")
        self.sg_tree.column("eq", width=60, anchor=tk.CENTER)
        self.sg_tree.tag_configure(
            "ocupado", font=("Segoe UI", 9, "bold"), foreground=NEON)
        sb1 = ttk.Scrollbar(izq, orient=tk.VERTICAL,
                            command=self.sg_tree.yview)
        self.sg_tree.configure(yscrollcommand=sb1.set)
        self.sg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb1.pack(side=tk.RIGHT, fill=tk.Y)
        self.sg_tree.bind("<<TreeviewSelect>>", self._on_subgrupo)

        # --- 2) Alimentos intercambiables del subgrupo ---
        cen = ttk.LabelFrame(
            columnas, text="Alimentos intercambiables (SMAE)", padding=4)
        cen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        busca = ttk.Frame(cen, style="Gym.TFrame")
        busca.pack(fill=tk.X)
        ttk.Label(busca, text="Buscar:", style="Gym.TLabel").pack(
            side=tk.LEFT, padx=(0, 4))
        self.busca_var = tk.StringVar()
        ttk.Entry(busca, textvariable=self.busca_var, width=18,
                  style="Gym.TEntry").pack(side=tk.LEFT)
        self.busca_var.trace_add(
            "write", lambda *_: self._refrescar_alimentos())
        tk.Button(
            busca, text="➕ AGREGAR", command=self.agregar_seleccion,
            font=("Impact", 8), fg=NEGRO, bg=NEON, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=8, pady=2,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=6)
        cols = ("alimento", "cantidad", "unidad", "peso_neto", "peso_bruto")
        self.alim_tree = ttk.Treeview(
            cen, columns=cols, show="headings", height=16,
            style="Gym.Treeview", selectmode="extended",
        )
        for col, texto, ancho, ancla in (
            ("alimento", "Alimento", 170, tk.W),
            ("cantidad", "Cantidad", 60, tk.CENTER),
            ("unidad", "Unidad", 70, tk.CENTER),
            ("peso_neto", "P. neto", 60, tk.E),
            ("peso_bruto", "P. bruto", 60, tk.E),
        ):
            self.alim_tree.heading(col, text=texto)
            self.alim_tree.column(col, width=ancho, anchor=ancla)
        sb2 = ttk.Scrollbar(cen, orient=tk.VERTICAL,
                            command=self.alim_tree.yview)
        self.alim_tree.configure(yscrollcommand=sb2.set)
        self.alim_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 3) Lista para imprimir ---
        der = ttk.LabelFrame(
            columnas, text="Lista para imprimir (canjes elegidos)",
            padding=4)
        der.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.sel_tree = ttk.Treeview(
            der, columns=("alimento", "cantidad", "unidad", "peso"),
            show="headings", height=16, style="Gym.Treeview",
            selectmode="browse",
        )
        for col, texto, ancho, ancla in (
            ("alimento", "Alimento", 150, tk.W),
            ("cantidad", "Cant.", 45, tk.CENTER),
            ("unidad", "Unidad", 60, tk.CENTER),
            ("peso", "Peso", 55, tk.E),
        ):
            self.sel_tree.heading(col, text=texto)
            self.sel_tree.column(col, width=ancho, anchor=ancla)
        sb3 = ttk.Scrollbar(der, orient=tk.VERTICAL,
                            command=self.sel_tree.yview)
        self.sel_tree.configure(yscrollcommand=sb3.set)
        self.sel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb3.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(
            der, text="🗑 QUITAR", command=self.quitar_seleccion,
            font=("Impact", 8), fg=NEGRO, bg=GRIS, activebackground=NARANJA,
            activeforeground=BLANCO, relief="flat", padx=8, pady=2,
            cursor="hand2",
        ).pack(anchor=tk.W, pady=(4, 0))

    # ------------------------------------------------------------------
    def cargar(self, paciente_id):
        self.paciente_id = paciente_id
        paciente = database.obtener_paciente(paciente_id) or {}
        self.lbl_estado.configure(
            text=f"Paciente: {paciente.get('nombre') or paciente_id}")
        self._refrescar_todo()

    def refrescar(self):
        self._refrescar_todo()

    def _distribucion(self):
        tab = getattr(self.app, "tab_equivalentes", None)
        return getattr(tab, "dist_datos", None) or {}

    def _eq_del_dia(self, dia, sg):
        valores = (self._distribucion().get(dia) or {}).get("valores") or []
        if sg >= len(valores):
            return 0.0
        total = 0.0
        for v in valores[sg]:
            try:
                total += float(v or 0)
            except (TypeError, ValueError):
                pass
        return total

    def _refrescar_todo(self):
        dist = self._distribucion()
        dias = [d for d in dist if any(
            any(v for v in fila)
            for fila in (dist[d].get("valores") or []))]
        self.dia_combo["values"] = dias
        if dias and self.dia_var.get() not in dias:
            self.dia_var.set(dias[0])
        if not dias:
            self.dia_var.set("")
        self._refrescar_subgrupos()
        self._refrescar_alimentos()

    def _refrescar_subgrupos(self):
        self.sg_tree.delete(*self.sg_tree.get_children())
        dia = self.dia_var.get()
        if not dia:
            return
        for sg, corto in enumerate(SUBGRUPOS_CORTO):
            eq = self._eq_del_dia(dia, sg)
            if eq > 0:
                self.sg_tree.insert(
                    "", tk.END, iid=str(sg), open=False,
                    text=corto, values=(f"{eq:g}",), tags=("ocupado",))

    def _on_subgrupo(self, _event=None):
        self._refrescar_alimentos()

    def _refrescar_alimentos(self):
        self.alim_tree.delete(*self.alim_tree.get_children())
        self._alimentos_actual = []
        sel = self.sg_tree.selection()
        if not sel:
            return
        try:
            sg = int(sel[0])
        except ValueError:
            return
        grupo = SUBGRUPOS[sg]
        texto = self.busca_var.get().strip().lower()
        for a in database.get_smae_alimentos_por_grupo(grupo):
            nombre = a.get("alimento") or ""
            if texto and texto not in nombre.lower():
                continue
            self._alimentos_actual.append(a)
            cs = a.get("cantidad_sugerida") or 0
            self.alim_tree.insert("", tk.END, values=(
                nombre,
                f"{cs:g}" if cs else "—",
                a.get("unidad") or "—",
                f"{a.get('peso_neto_g') or 0:g}",
                f"{a.get('peso_bruto_g') or 0:g}",
            ))

    def agregar_seleccion(self):
        sel = self.alim_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Alimentos intercambiables",
                "Selecciona uno o varios alimentos de la tabla central.")
            return
        sg_sel = self.sg_tree.selection()
        if not sg_sel:
            messagebox.showwarning(
                "Alimentos intercambiables", "Selecciona un subgrupo.")
            return
        try:
            sg = int(sg_sel[0])
        except ValueError:
            return
        lista = self.seleccion.setdefault(sg, [])
        for item in sel:
            try:
                pos = self.alim_tree.index(item)
            except Exception:
                continue
            if not (0 <= pos < len(self._alimentos_actual)):
                continue
            a = self._alimentos_actual[pos]
            nombre = a.get("alimento") or ""
            if any(x.get("alimento") == nombre for x in lista):
                continue
            lista.append(dict(a))
        self._refrescar_seleccion()

    def quitar_seleccion(self):
        sel = self.sel_tree.selection()
        if not sel:
            return
        for item in sel:
            try:
                sg, pos = str(item).split(":")
                sg, pos = int(sg), int(pos)
            except (ValueError, AttributeError):
                continue
            lista = self.seleccion.get(sg, [])
            if 0 <= pos < len(lista):
                lista.pop(pos)
            if not lista:
                self.seleccion.pop(sg, None)
        self._refrescar_seleccion()

    def limpiar_lista(self):
        self.seleccion = {}
        self._refrescar_seleccion()

    def _refrescar_seleccion(self):
        self.sel_tree.delete(*self.sel_tree.get_children())
        for sg in sorted(self.seleccion):
            for pos, reg in enumerate(self.seleccion[sg]):
                cs = reg.get("cantidad_sugerida") or 0
                self.sel_tree.insert(
                    "", tk.END, iid=f"{sg}:{pos}", open=False,
                    values=(
                        reg.get("alimento") or "",
                        f"{cs:g}" if cs else "—",
                        reg.get("unidad") or "—",
                        f"{reg.get('peso_neto_g') or 0:g}",
                    ))

    def generar_pdf(self):
        if not self.seleccion:
            messagebox.showwarning(
                "Alimentos intercambiables",
                "La lista para imprimir está vacía.")
            return
        dia = self.dia_var.get() or "—"
        secciones = []
        for sg in sorted(self.seleccion):
            registros = self.seleccion[sg]
            if not registros:
                continue
            corto = SUBGRUPOS_CORTO[sg] if sg < len(SUBGRUPOS_CORTO) else "?"
            secciones.append((corto, self._eq_del_dia(dia, sg), registros))
        paciente_id = getattr(self.app, "id_paciente_antro", None)
        paciente = database.obtener_paciente(paciente_id) or {} \
            if paciente_id else {}
        nombre = (paciente.get("nombre") or "paciente").strip() or "paciente"
        ruta = os.path.join(
            os.environ.get("TEMP", os.getcwd()),
            f"Intercambiables_{nombre.replace(' ', '_')}_"
            f"{datetime.now().strftime('%Y%m%d')}.pdf")
        generar_pdf_intercambiables(ruta, paciente, dia, secciones)
        try:
            abrir_para_imprimir(ruta)
        except Exception as error:
            messagebox.showinfo(
                "Alimentos intercambiables",
                f"PDF generado:\n{ruta}\n\nNo se pudo abrir: {error}")
            return
        messagebox.showinfo(
            "Alimentos intercambiables", f"PDF generado:\n{ruta}")
