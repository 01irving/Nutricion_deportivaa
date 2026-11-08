"""
Genera la guía educativa «Alimentos a evitar» (PDF) en la carpeta de
recomendaciones, con el mismo estilo editorial de las guías existentes.

Fuente: Bytomski JR. Fueling for Performance. Sports Health.
2018;10(1):47-53.

Uso:
    python crear_pdf_alimentos_a_evitar.py
"""
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, KeepTogether, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

RUTA = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RUTA, 'recomendaciones', 'Educación nutricional',
                       'Alimentos a evitar.pdf')

TITULO = 'Alimentos a evitar'
SUBTITULO = 'Qué limitar para rendir y recuperarte mejor'
FECHA = 'Noviembre de 2026'

TINTA = colors.HexColor('#1E1E24')
TURQUESA = colors.HexColor('#3A8FA8')
GRIS = colors.HexColor('#5A5A5A')
GRIS_CLARO = colors.HexColor('#8A8A8A')
LINEA = colors.HexColor('#D9D4C7')
FONDO = colors.HexColor('#EEF6F8')
ROJO_SUAVE = colors.HexColor('#FBEDEA')

ANCHO, ALTO = A4
MARGEN = 2.3 * cm

# ---------------------------------------------------------------- estilos --
E = {
    'kicker': ParagraphStyle('kicker', fontName='Helvetica-Bold', fontSize=8,
                             leading=10, textColor=GRIS, spaceAfter=0),
    'portada1': ParagraphStyle('portada1', fontName='Times-Bold',
                               fontSize=44, leading=46, textColor=TINTA),
    'portada2': ParagraphStyle('portada2', fontName='Times-Bold',
                               fontSize=44, leading=48, textColor=TURQUESA),
    'portada_sub': ParagraphStyle('portada_sub', fontName='Times-Italic',
                                  fontSize=17, leading=22, textColor=TINTA),
    'intro': ParagraphStyle('intro', fontName='Helvetica', fontSize=9.5,
                            leading=15, textColor=GRIS),
    'dato': ParagraphStyle('dato', fontName='Times-Bold', fontSize=15,
                           leading=17, textColor=TINTA),
    'dato_et': ParagraphStyle('dato_et', fontName='Helvetica', fontSize=6.5,
                              leading=9, textColor=GRIS_CLARO),
    'pie_portada': ParagraphStyle('pie_portada', fontName='Helvetica',
                                  fontSize=7.5, leading=9, textColor=GRIS,
                                  alignment=1),
    'contenido': ParagraphStyle('contenido', fontName='Times-Bold',
                                fontSize=22, leading=26, textColor=TINTA),
    'h1': ParagraphStyle('h1', fontName='Times-Bold', fontSize=18,
                         leading=22, textColor=TINTA, spaceBefore=14,
                         spaceAfter=6),
    'h2': ParagraphStyle('h2', fontName='Times-Bold', fontSize=12.5,
                         leading=16, textColor=TURQUESA, spaceBefore=10,
                         spaceAfter=4),
    'p': ParagraphStyle('p', fontName='Helvetica', fontSize=10, leading=15,
                        textColor=TINTA, spaceAfter=6, alignment=TA_LEFT),
    'vi': ParagraphStyle('vi', fontName='Helvetica', fontSize=10, leading=14,
                         textColor=TINTA, leftIndent=14, bulletIndent=2,
                         spaceAfter=3),
    'cita': ParagraphStyle('cita', fontName='Times-Italic', fontSize=13,
                           leading=18, textColor=TURQUESA, leftIndent=12,
                           spaceBefore=4, spaceAfter=8),
    'caja': ParagraphStyle('caja', fontName='Helvetica', fontSize=9.5,
                           leading=14, textColor=TINTA),
    'caja_t': ParagraphStyle('caja_t', fontName='Helvetica-Bold',
                             fontSize=8, leading=11, textColor=TURQUESA),
    'th': ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=9,
                         leading=12, textColor=colors.white),
    'td': ParagraphStyle('td', fontName='Helvetica', fontSize=9,
                         leading=12.5, textColor=TINTA),
    'ref': ParagraphStyle('ref', fontName='Helvetica', fontSize=8.5,
                          leading=12.5, textColor=GRIS, leftIndent=14,
                          firstLineIndent=-14, spaceAfter=5),
    'toc1': ParagraphStyle('toc1', fontName='Times-Bold', fontSize=11.5,
                           leading=16, textColor=TINTA, spaceBefore=8),
    'toc2': ParagraphStyle('toc2', fontName='Times-Roman', fontSize=9.5,
                           leading=13, textColor=GRIS, leftIndent=16),
}


class Guia(BaseDocTemplate):
    """Documento con portada, encabezado/pie y tabla de contenido."""

    def __init__(self, ruta):
        super().__init__(ruta, pagesize=A4, title=TITULO,
                         author='Nutrición deportiva',
                         subject=SUBTITULO, leftMargin=MARGEN,
                         rightMargin=MARGEN, topMargin=2.4 * cm,
                         bottomMargin=2.2 * cm)
        marco = Frame(MARGEN, 2.2 * cm, ANCHO - 2 * MARGEN,
                      ALTO - 4.6 * cm, id='cuerpo')
        portada = Frame(MARGEN, 2.2 * cm, ANCHO - 2 * MARGEN,
                        ALTO - 4.2 * cm, id='portada')
        self.addPageTemplates([
            PageTemplate('portada', [portada], onPage=self._pie_portada),
            PageTemplate('cuerpo', [marco], onPage=self._encabezado),
        ])

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            estilo = flowable.style.name
            if estilo in ('h1', 'h2'):
                nivel = 0 if estilo == 'h1' else 1
                self.notify('TOCEntry', (nivel, flowable.getPlainText(),
                                         self.page))

    @staticmethod
    def _pie_portada(canv, doc):
        canv.saveState()
        canv.setStrokeColor(LINEA)
        canv.setLineWidth(0.8)
        canv.line(MARGEN, 2.6 * cm, ANCHO - MARGEN, 2.6 * cm)
        canv.setFont('Helvetica', 7.5)
        canv.setFillColor(GRIS)
        canv.drawCentredString(ANCHO / 2, 2.0 * cm,
                               'Material educativo para pacientes y '
                               'deportistas')
        canv.restoreState()

    @staticmethod
    def _encabezado(canv, doc):
        canv.saveState()
        canv.setFont('Helvetica', 7)
        canv.setFillColor(GRIS)
        y = ALTO - 1.5 * cm
        canv.drawString(MARGEN, y, 'NUTRICIÓN DEPORTIVA · GUÍA EDUCATIVA')
        canv.drawRightString(ANCHO - MARGEN, y, TITULO.upper())
        canv.setStrokeColor(LINEA)
        canv.setLineWidth(0.6)
        canv.line(MARGEN, y - 6, ANCHO - MARGEN, y - 6)
        canv.line(MARGEN, 1.6 * cm, ANCHO - MARGEN, 1.6 * cm)
        canv.drawString(MARGEN, 1.15 * cm, f'{TITULO}: {SUBTITULO.lower()}')
        canv.drawRightString(ANCHO - MARGEN, 1.15 * cm, f'Página {doc.page}')
        canv.restoreState()


# ------------------------------------------------------------- utilidades --
def p(texto):
    return Paragraph(texto, E['p'])


def vinetas(items):
    return [Paragraph(t, E['vi'], bulletText='•') for t in items]


def caja(titulo, texto, fondo=FONDO, borde=TURQUESA):
    t = Table([[Paragraph(titulo.upper(), E['caja_t'])],
               [Paragraph(texto, E['caja'])]],
              colWidths=[ANCHO - 2 * MARGEN])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), fondo),
        ('LINEBEFORE', (0, 0), (0, -1), 3, borde),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
    ]))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 8)])


def tabla(encabezados, filas, anchos):
    datos = [[Paragraph(h, E['th']) for h in encabezados]]
    datos += [[Paragraph(c, E['td']) for c in f] for f in filas]
    t = Table(datos, colWidths=anchos, repeatRows=1)
    estilo = [
        ('BACKGROUND', (0, 0), (-1, 0), TURQUESA),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, LINEA),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(datos)):
        if i % 2 == 0:
            estilo.append(('BACKGROUND', (0, i), (-1, i), FONDO))
    t.setStyle(TableStyle(estilo))
    return t


# --------------------------------------------------------------- portada --
def portada():
    ancho = ANCHO - 2 * MARGEN
    datos = Table(
        [[Paragraph('&lt;10 %', E['dato']), Paragraph('0 g', E['dato']),
          Paragraph('7 kcal/g', E['dato']),
          Paragraph(FECHA, ParagraphStyle(
              'f', parent=E['dato_et'], fontSize=7.5, textColor=GRIS))],
         [Paragraph('GRASA SATURADA', E['dato_et']),
          Paragraph('GRASAS TRANS', E['dato_et']),
          Paragraph('ALCOHOL, SIN NUTRIENTES', E['dato_et']), '']],
        colWidths=[ancho * 0.2, ancho * 0.2, ancho * 0.3, ancho * 0.3])
    datos.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
    ]))
    return [
        Spacer(1, 1.2 * cm),
        Paragraph('G U Í A &nbsp; E D U C A T I V A &nbsp; · &nbsp; '
                  'N U T R I C I Ó N &nbsp; D E P O R T I V A', E['kicker']),
        Spacer(1, 12),
        HRFlowable(width=1.2 * cm, thickness=2.5, color=TURQUESA,
                   hAlign='LEFT', spaceAfter=18),
        Paragraph('Alimentos', E['portada1']),
        Paragraph('a evitar', E['portada2']),
        Spacer(1, 10),
        Paragraph(SUBTITULO, E['portada_sub']),
        Spacer(1, 18),
        HRFlowable(width='70%', thickness=0.6, color=LINEA, hAlign='LEFT',
                   spaceAfter=14),
        Paragraph(
            'Comer bien no es solo sumar buenos alimentos: también es '
            'reconocer los que frenan tu rendimiento, tu recuperación y tu '
            'salud. Esta guía explica, con base científica y en lenguaje '
            'sencillo, qué alimentos y hábitos conviene evitar o limitar '
            'si entrenas, por qué, y con qué sustituirlos.', E['intro']),
        Spacer(1, 7.5 * cm),
        datos,
        NextPageTemplate('cuerpo'),
        PageBreak(),
    ]


# ------------------------------------------------------------- contenido --
def cuerpo():
    toc = TableOfContents()
    toc.levelStyles = [E['toc1'], E['toc2']]
    toc.dotsMinLevel = 0

    h = []
    h += [Paragraph('Contenido', E['contenido']),
          HRFlowable(width='100%', thickness=0.6, color=TINTA,
                     spaceBefore=4, spaceAfter=12), toc, PageBreak()]

    # 1 -----------------------------------------------------------------
    h.append(Paragraph('1. La regla de oro: comida real', E['h1']))
    h.append(Paragraph('«Come comida (real), sobre todo verduras, y no '
                       'demasiada».', E['cita']))
    h.append(p(
        'La frase de Michael Pollan resume lo que la evidencia recomienda '
        'a los deportistas: obtener proteínas, carbohidratos, grasas, '
        'vitaminas y minerales de una <b>gran variedad de alimentos '
        'enteros</b>. Siempre que se pueda, la comida de verdad es mejor '
        'opción que los productos empacados, las barras y los licuados '
        'comerciales.'))
    h.append(p(
        'Evitar un alimento no significa prohibirlo para siempre. Lo que '
        'cuenta es <b>qué tan seguido y en qué cantidad</b> aparece en tu '
        'semana. Los grupos de esta guía son los que con más frecuencia '
        'desplazan a los alimentos que sí te nutren o que interfieren con '
        'tu entrenamiento.'))
    h.append(caja(
        'Licuados: sí, pero caseros',
        'Un licuado puede ser una buena fuente de nutrientes si se prepara '
        'con ingredientes enteros y <b>sin azúcar añadido</b>. Ejemplo: 1 '
        'taza de bebida de almendra sin azúcar, 1 taza de plátano o '
        'frutos rojos congelados, 1 cucharada de aceite de coco, 1 taza de '
        'yogurt griego natural y 1-2 medidas de proteína en polvo '
        '(≈ 400 kcal, 30 g de proteína y 30-50 g de carbohidratos).'))

    # 2 -----------------------------------------------------------------
    h.append(Paragraph('2. Azúcares añadidos y ultraprocesados', E['h1']))
    h.append(Paragraph('2.1 No todos los carbohidratos son iguales', E['h2']))
    h.append(p(
        'Los carbohidratos son el combustible principal del ejercicio '
        'intenso, pero hay una gran diferencia entre <b>un plato de avena '
        'y un plato de helado</b>. Los granos enteros, las frutas, las '
        'verduras y las leguminosas aportan fibra, vitaminas, minerales y '
        'antioxidantes; los azúcares procesados, tan abundantes en la '
        'dieta occidental, pueden ser bastante perjudiciales para la '
        'salud.'))
    h.append(Paragraph('2.2 Qué evitar o limitar', E['h2']))
    h += vinetas([
        'Refrescos, jugos industrializados, aguas de sabor y bebidas '
        'energéticas azucaradas.',
        'Pan dulce, galletas, pastelitos, donas y panqués empacados.',
        'Cereales de caja azucarados y barras de granola con azúcar '
        'añadido.',
        'Dulces, chocolates con leche, golosinas y helado.',
        'Licuados, «smoothies» y malteadas comerciales con jarabes o '
        'azúcar.',
        'Botanas y comida rápida: papas fritas, frituras, nuggets, '
        'hamburguesas de cadena.',
    ])
    h.append(Paragraph('2.3 Por qué', E['h2']))
    h.append(p(
        'Aportan mucha energía con pocos nutrientes, desplazan a los '
        'alimentos que sí reparan y protegen tu cuerpo. Además, el '
        'ejercicio aumenta la producción de radicales libres: conviene '
        '<b>evitar los alimentos que aumentan el estrés oxidativo</b> y '
        'preferir los ricos en antioxidantes, como frutas y verduras.'))

    # 3 -----------------------------------------------------------------
    h.append(Paragraph('3. Grasas trans y exceso de grasa saturada',
                       E['h1']))
    h.append(p(
        'La grasa es indispensable: forma las membranas de las células, '
        'permite absorber las vitaminas A, D, E y K, regula hormonas y es '
        'combustible para el músculo. Por eso la recomendación <b>no</b> '
        'es eliminarla, sino cuidar su calidad: del 20 al 35 % de las '
        'calorías del día deben venir de grasas saludables, y no conviene '
        'bajar de 15-20 %.'))
    h.append(Paragraph('3.1 Grasas trans: evitarlas por completo', E['h2']))
    h += vinetas([
        'Productos con «aceite vegetal parcialmente hidrogenado» en la '
        'etiqueta.',
        'Margarinas sólidas y manteca vegetal.',
        'Pan dulce, galletas y pastelería industrial.',
        'Frituras comerciales y palomitas de microondas con mantequilla.',
    ])
    h.append(Paragraph('3.2 Grasa saturada: menos del 10 %', E['h2']))
    h += vinetas([
        'Embutidos: chorizo, salchicha, tocino, longaniza, salami.',
        'Carnes con mucha grasa visible y piel de pollo.',
        'Exceso de crema, mantequilla y quesos maduros.',
    ])
    h.append(caja(
        'Mejor elige',
        'Salmón y otros pescados, nueces y cremas de nueces naturales, '
        'aguacate y aceite de oliva. Los omega-3 (salmón, linaza, chía) '
        'ayudan a contrarrestar la inflamación y los radicales libres que '
        'genera el entrenamiento.'))

    # 4 -----------------------------------------------------------------
    h.append(Paragraph('4. Alcohol', E['h1']))
    h.append(p(
        'El alcohol no es un macronutriente, pero aporta <b>7 kcal por '
        'gramo</b> sin vitaminas ni minerales. Por eso se desaconseja '
        'para entrenar con buenos resultados y para la salud en general.'))
    h += vinetas([
        '<b>Frena la recuperación:</b> altera la síntesis de proteína '
        'muscular, el proceso que reconstruye el músculo después del '
        'ejercicio.',
        '<b>En una lesión, peor:</b> durante la recuperación de una lesión '
        'conviene limitarlo o eliminarlo para no perder más músculo.',
    ])

    # 5 -----------------------------------------------------------------
    h.append(Paragraph('5. Dietas de moda y pérdida de peso rápida',
                       E['h1']))
    h.append(p(
        'Muchos deportistas recurren a dietas de moda o a métodos '
        'extremos para «dar el peso». Estas prácticas tienen efectos '
        'dañinos: <b>deshidratación, pérdida de las reservas de glucógeno '
        'y pérdida de masa muscular</b>.'))
    h.append(Paragraph('5.1 Hábitos a evitar', E['h2']))
    h += vinetas([
        '<b>Deshidratarse a propósito</b> (sudar con plásticos, sauna, '
        'dejar de tomar agua). Perder más del 2 % del peso corporal en '
        'sudor disminuye la concentración y el rendimiento; la sed llega '
        'tarde: se puede perder hasta 1.5 L antes de sentirla.',
        '<b>Comer demasiado poco</b>. Si la energía que queda después del '
        'ejercicio baja de 30 kcal por kg de masa libre de grasa al día, '
        'se alteran muchas funciones del cuerpo; en mujeres deportistas '
        'se asocia con fracturas por estrés y baja densidad ósea.',
        '<b>Eliminar grupos completos de alimentos</b> sin supervisión: '
        'aumenta el riesgo de deficiencia de hierro, vitamina D, calcio y, '
        'en dietas vegetarianas, vitamina B12 y zinc.',
        '<b>Quitar el gluten sin indicación médica</b>. La gran mayoría de '
        'las personas no necesita evitarlo, y los granos enteros tienen '
        'muchos beneficios para la salud.',
        '<b>Dietas muy bajas en carbohidratos</b> si haces ejercicio '
        'intenso: el cuerpo no obtiene energía de la grasa con la rapidez '
        'que exige el esfuerzo de alta intensidad.',
    ])

    # 6 -----------------------------------------------------------------
    h.append(Paragraph('6. Combinaciones y momentos a evitar', E['h1']))
    h.append(Paragraph('6.1 Alrededor del entrenamiento', E['h2']))
    h += vinetas([
        '<b>Antes:</b> limita la grasa; en la comida previa al ejercicio '
        'puede causar molestias gastrointestinales.',
        '<b>Durante:</b> en sesiones de menos de 60 minutos no necesitas '
        'bebidas azucaradas ni geles; basta con agua.',
    ])
    h.append(Paragraph('6.2 Café o té con el suplemento de hierro', E['h2']))
    h.append(p(
        'Los polifenoles del café y del té reducen la absorción del '
        'hierro. Si te indicaron hierro, <b>no lo tomes con café o té</b>; '
        'tómalo con una fuente de vitamina C (jugo de naranja, guayaba, '
        'kiwi) para absorberlo mejor.'))
    h.append(Paragraph('6.3 Megadosis de vitaminas sin indicación', E['h2']))
    h += vinetas([
        'Las vitaminas C y E a dosis altas pueden volverse '
        '<b>pro-oxidantes</b>, y el exceso de vitamina E interfiere con la '
        'vitamina K y la coagulación.',
        'La vitamina D se acumula en el cuerpo: suplementarla sin control '
        'puede causar náusea, vómito, debilidad, confusión y alteraciones '
        'del ritmo cardiaco. Tómala solo con indicación y seguimiento.',
    ])

    # 7 -----------------------------------------------------------------
    h.append(Paragraph('7. Cambios prácticos', E['h1']))
    h.append(p('Pequeñas sustituciones hacen la mayor diferencia:'))
    ancho = ANCHO - 2 * MARGEN
    h.append(tabla(
        ['En lugar de…', 'Elige…'],
        [
            ['Refresco, jugo industrializado o agua de sabor',
             'Agua natural, agua mineral con limón o agua de fruta natural '
             'sin azúcar'],
            ['Bebida energética o deportiva sin necesidad',
             'Agua; la bebida deportiva solo en sesiones largas (más de '
             '60 min)'],
            ['Cereal de caja azucarado', 'Avena con fruta'],
            ['Pan dulce, galletas o pastelitos',
             'Pan integral, fruta entera o yogurt natural'],
            ['Helado', 'Yogurt griego natural con fruta'],
            ['Barras y licuados comerciales con azúcar',
             'Licuado casero con fruta, yogurt griego y proteína'],
            ['Papas fritas y frituras',
             'Un puño de almendras o nueces, palomitas naturales hechas en '
             'casa'],
            ['Embutidos (salchicha, chorizo, tocino)',
             'Pechuga de pollo, pescado, huevo o queso cottage'],
            ['Margarina o manteca', 'Aceite de oliva o aguacate'],
            ['Bebidas alcohólicas',
             'Agua mineral con limón o bebidas sin alcohol y sin azúcar'],
        ],
        [ancho * 0.45, ancho * 0.55]))

    # 8 -----------------------------------------------------------------
    h.append(Paragraph('8. Mensajes clave', E['h1']))
    h += vinetas([
        'Basa tu alimentación en <b>comida real</b>: verduras, frutas, '
        'granos enteros, leguminosas, proteínas magras y grasas '
        'saludables.',
        'Limita los <b>azúcares añadidos y ultraprocesados</b>; no aportan '
        'lo que tu cuerpo necesita para entrenar y recuperarse.',
        'Elimina las <b>grasas trans</b> y mantén la grasa saturada por '
        'debajo del 10 % de tus calorías.',
        'Evita el <b>alcohol</b>, sobre todo en periodos de entrenamiento '
        'intenso o de recuperación de una lesión.',
        'Desconfía de las <b>dietas de moda</b> y de la pérdida de peso '
        'rápida: cuestan músculo, glucógeno e hidratación.',
        'Cualquier restricción especial (gluten, lactosa, proteína por '
        'enfermedad renal, suplementos) debe indicarla tu profesional de '
        'la salud.',
    ])
    h.append(caja(
        'Importante',
        'Esta guía es orientativa. Tu nutriólogo ajustará las '
        'recomendaciones a tu deporte, tus objetivos y tu estado de '
        'salud.', fondo=ROJO_SUAVE, borde=colors.HexColor('#D9775F')))

    # Referencias --------------------------------------------------------
    h.append(Paragraph('Referencia', E['h1']))
    h.append(Paragraph(
        'Bytomski JR. Fueling for performance. <i>Sports Health</i>. '
        '2018;10(1):47-53. doi:10.1177/1941738117743913', E['ref']))
    return h


def main():
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    doc = Guia(DESTINO)
    doc.multiBuild(portada() + cuerpo())
    print('PDF creado:', DESTINO)


if __name__ == '__main__':
    main()
