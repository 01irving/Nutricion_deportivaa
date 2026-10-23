"""
Catálogo de suplementos deportivos por categoría.

Cada suplemento incluye:
  - categoria: familia funcional (Energía y rendimiento, Recuperación, etc.)
  - grupo: clasificación IOC (A = uso comprobado, B = en estudio,
           C = otros / no clasificados)
  - posologia: dosis y momento de administración de referencia
  - para_que_sirve: efecto principal
  - cuidados: advertencias, contraindicaciones e interacciones
"""

GRUPO_A = "Grupo A - Uso comprobado"
GRUPO_B = "Grupo B - En estudio"
GRUPO_C = "Grupo C - Otros / no clasificados"

CATALOGO = [
    # ------------------------------------------------------------------
    # ENERGÍA Y RENDIMIENTO
    # ------------------------------------------------------------------
    {
        "categoria": "Energía y rendimiento",
        "grupo": GRUPO_A,
        "nombre": "Cafeína",
        "posologia": "3-6 mg/kg de masa corporal; máximo 9 mg/kg/día. "
        "Ingerir 30-60 min antes del esfuerzo. En dosis altas (>6 mg/kg) "
        "puede dividirse en 2/3 pre-esfuerzo y 1/3 durante lacompetition.",
        "para_que_sirve": "Aumenta la alerta, reduce la percepción de "
        "esfuerzo y mejora la resistencia en esfuerzos de 30-120 min. Es "
        "el suplemento con mayor evidencia en el consenso del IOC.",
        "cuidados": "No usar en menores de 18 años ni en personas con "
        "hipertensión, arritmias, ansiedad o insomnio. Interactúa con la "
        "teofilina. Evitar combinarlo con bebidas energizantes. Reduce "
        "el sueño y el apetito: no tomarla más de 8-10 h antes de dormir.",
    },
    {
        "categoria": "Energía y rendimiento",
        "grupo": GRUPO_A,
        "nombre": "Creatina monohidrato",
        "posologia": "3-5 g/día en dosis única diaria, con o sin comida. "
        "Periodo de carga opcional: 20 g/día (4 x 5 g) durante 5-6 días, "
        "seguido de 3-5 g/día de mantenimiento.",
        "para_que_sirve": "Aumenta la fosfocreatina muscular, mejora la "
        "potencia, la fuerza y el rendimiento en esfuerzos cortos "
        "repetidos (fuerza, potencia, intervalos de alta intensidad).",
        "cuidados": "Puede causar retención de agua (1-2 kg) y ligeras "
        "molestias gastrointestinales si se toma en dosis altas. Debe "
        "ingerirse con suficiente agua. No es necesaria la fase de carga. "
        "Sin riesgo de toxicidad a dosis recomendadas en personas con "
        "riñones sanos, pero consultar en insuficiencia renal.",
    },
    {
        "categoria": "Energía y rendimiento",
        "grupo": GRUPO_A,
        "nombre": "Proteína en polvo (whey / caseína)",
        "posologia": "0.3 g/kg/día de proteína extra (total 1.6-2.2 g/kg/día "
        "en atletas de fuerza). Distribuir en 3-4 tomas de 0.4 g/kg. "
        "Post-ejercicio: 20-40 g de proteína de alta calidad. En ayuno: "
        "caseína 30-40 g.",
        "para_que_sirve": "Aporta aminoácidos para la síntesis de "
        "proteína muscular, la reparación de tejidos y la recuperación. "
        "Útil cuando la ingesta dietética es insuficiente.",
        "cuidados": "Elegir productos con sello de terceros (NSF, "
        "Informed Sport, USP) por riesgo de contaminación. No es "
        "mágico: el beneficio real depende de la ingesta total de proteína. "
        "Usar con precaución en insuficiencia renal o alergia a la "
        "proteína de la leche.",
    },
    {
        "categoria": "Energía y rendimiento",
        "grupo": GRUPO_A,
        "nombre": "Nitrato de sodio / Jugo de remolacha",
        "posologia": "Nitrato: 5-9 mmol (300-540 mg) 2-3 h antes del "
        "esfuerzo, idealmente en 2-3 dosis separadas en las 24 h previas. "
        "Concentrado de remolacha: 70-140 ml 2-3 h antes.",
        "para_que_sirve": "Aumenta el óxido nitrírico (NO), mejora la "
        "eficiencia muscular y puede extender el rendimiento en esfuerzos "
        "de alta intensidad de 4-30 min y en pruebas de resistencia.",
        "cuidados": "Puede tintar la orina y las heces de rosado. "
        "Contraindicado en hipotensión, en tratamiento con inhibidores de "
        "PDE5 y en profilaxis con tadCy. Usar con precaución con "
        "antibióticos orales. El efecto se atenúa con colutorio "
        "antibacteriano.",
    },
    {
        "categoria": "Energía y rendimiento",
        "grupo": GRUPO_A,
        "nombre": "Bicarbonato de sodio",
        "posologia": "0.2-0.3 g/kg de masa corporal (máx. 300 g), "
        "90-120 min antes, disuelto en agua con algo de azúcar. "
        "Ensayos de 1-10 min de alta intensidad.",
        "para_que_sirve": "Actúa como buffer extracelular: retrasa la "
        "fatiga por acidosis y mejora el rendimiento en esfuerzos de "
        "1-10 min, series de alta intensidad y deportes de equipo.",
        "cuidados": "Causa molestias gastrointestinales, diarrea, "
        "vómitos y retención de líquidos (2-4 kg). No usar en atletas con "
        "hipertensión, insuficiencia renal o historial de lesiones por "
        "estrés. Requiere ensayo previo, nunca en competición. Riesgo "
        "de deshidratación y alcalosis metabólica.",
    },
    {
        "categoria": "Energía y rendimiento",
        "grupo": GRUPO_A,
        "nombre": "Beta-alanina",
        "posologia": "4-6.4 g/día fraccionados en 4-6 dosis de 0.8-1.6 g "
        "durante 4-8 semanas. Tomar con comida.",
        "para_que_sirve": "Aumenta la carnosina muscular, que funciona "
        "como buffer ácido. Mejora el rendimiento en esfuerzos de alta "
        "intensidad de 1-4 min y en repeticiones de fuerza de 30-240 s.",
        "cuidados": "Causa hormigueo y ardor en la piel (parestesia) en "
        "dosis altas; se reduce con comida y dividiendo la dosis. Seguro "
        "en personas sanas. El beneficio aparece tras 4-6 semanas.",
    },
    {
        "categoria": "Energía y rendimiento",
        "grupo": GRUPO_A,
        "nombre": "Geles y electrolitos (carbohidratos)",
        "posologia": "30-60 g de carbohidratos por hora de esfuerzo. "
        "Geles: 1-2 unidades por hora según intensidad. En esfuerzos "
        "superiores a 2.5 h usar con sodio (500-700 mg/h). Pre-hidratar "
        "400-600 ml/h 2-4 h antes.",
        "para_que_sirve": "Mantiene la glucemia y retrasa la fatiga "
        "central durante esfuerzos prolongados de resistencia y en "
        "deportes con pausas (fútbol, hockey).",
        "cuidados": "Probables molestias gastrointestinales si se excede "
        "la tolerancia (entrenar el intestino). Alto contenido de azúcar: "
        "cuidado con diabetes o intolerancia a la fructosa. Preferir "
        "carbohidratos de transporte mixto (glucosa + fructosa).",
    },
    # ------------------------------------------------------------------
    # RECUPERACIÓN Y FUERZA
    # ------------------------------------------------------------------
    {
        "categoria": "Recuperación y fuerza",
        "grupo": GRUPO_A,
        "nombre": "Sodio y electrolitos (hidratación)",
        "posologia": "600-1000 mg de sodio/h en esfuerzos mayores a 1 h o "
        "en calor. Reponer 125-150% de la pérdida de sudor por peso "
        "corporal perdido tras el ejercicio.",
        "para_que_sirve": "Mantiene el volumen plasmático, la "
        "termorregulación y la función neuromuscular durante esfuerzos "
        "largos en calor.",
        "cuidados": "El exceso de sodio puede causar deshidratación "
        "hipertónica, hipertensión y retención de líquidos. Vigilar en "
        "personas con insuficiencia renal, hipertensión o restricciones "
        "de sodio.",
    },
    {
        "categoria": "Recuperación y fuerza",
        "grupo": GRUPO_B,
        "nombre": "L-carnitina (L-carnitina L-tartarato)",
        "posologia": "2-3 g/día con 0.8-1.2 g de ácido alpha lipoico. "
        "Dividir en 2-3 dosis. Algunos estudios usan 1-2 g 1-2 semanas "
        "antes del esfuerzo.",
        "para_que_sirve": "Transporte de ácidos grasos de cadena larga "
        "hacia la mitocondria. Efecto modesto en resistencia y en "
        "recuperación ante daño muscular.",
        "cuidados": "Efecto marginal en sujetos con dieta adecuada. Puede "
        "causar olor corporal y molestias digestivas. Interactúa con "
        "anticoagulantes orales y con warfarina. Precaución en "
        "hipotiroidismo.",
    },
    {
        "categoria": "Recuperación y fuerza",
        "grupo": GRUPO_B,
        "nombre": "HMB (beta-hidroximi-beta-metilbutirato)",
        "posologia": "3 g/día, idealmente en 2-3 dosis de 1 g, "
        "preferentemente con comida rica en proteína.",
        "para_que_sirve": "Reduce la degradación de proteína muscular y el "
        "catabolismo. Puede ayudar en la recuperación ante cargas altas "
        "de volumen en periodos de sobrecarga.",
        "cuidados": "Evidencia limitada; el beneficio es mayor en "
        "principiantes, en personas de poca masa muscular y en periodos de "
        "restricción calórica. Seguro a corto plazo, siendo prudente "
        "monitorizar la función renal en uso prolongado.",
    },
    {
        "categoria": "Recuperación y fuerza",
        "grupo": GRUPO_B,
        "nombre": "Jugo de cereza (antocianinas)",
        "posologia": "30 mL (2 x 15 mL) de concentrado diluido 1:1 en agua "
        "7-10 días antes de la competición y durante la fase de "
        "competición. Aporta 480 mg de antocianinas/día.",
        "para_que_sirve": "Reduce el estrés oxidativo y la peroxidación "
        "lipídica muscular, lo que puede mejorar la recuperación y "
        "reducir el dolor muscular pos-ejercicio.",
        "cuidados": "Puede causar somnolencia leve y reacciones en la "
        "piel. Contiene azúcar. Interactúa con anticoagulantes "
        "(warfarina) al aumentar su efecto.",
    },
    {
        "categoria": "Recuperación y fuerza",
        "grupo": GRUPO_B,
        "nombre": "Glutamina",
        "posologia": "5 g antes y 5 g después del ejercicio, o 5 g/día en "
        "una sola toma. Endqreply: 5-10 g/día.",
        "para_que_sirve": "Aminoácido condicionalmente esencial en "
        "estrés. Apoya la síntesis proteica y la función inmune. Posible "
        "efecto sobre la recuperación del tubo digestivo.",
        "cuidados": "La suplementación de glutamina en atletas sanos no "
        "muestra beneficios claros (el IOC no la recomienda de forma "
        "rutinaria). Precaución en pacientes con tumor o insuficiencia "
        "renal.",
    },
    {
        "categoria": "Recuperación y fuerza",
        "grupo": GRUPO_C,
        "nombre": "Colágeno hidrolizado + vitamina C",
        "posologia": "15 g de colágeno hidrolizado + 50 mg de vitamina C "
        "30-60 min antes del entrenamiento o de la carga de impacto.",
        "para_que_sirve": "Aporta aminoácidos específicos del colágeno "
        "(glicina, prolina, hidroxiprolina) para apoyar la síntesis de "
        "tejido conectivo, tendones, ligamentos, cartílago y piel.",
        "cuidados": "Evidencia emergente: los estudios muestran mejoras en "
        "marcadores de síntesis de colágeno. No sustituye a la proteína "
        "completa. No exceder 1 g/día de vitamina C.",
    },
    # ------------------------------------------------------------------
    # SUEÑO Y SISTEMA NERVIOSO
    # ------------------------------------------------------------------
    {
        "categoria": "Regulación del sueño y sistema nervioso",
        "grupo": GRUPO_A,
        "nombre": "Melatonina",
        "posologia": "0.5-3 mg (preferiblemente 0.5-1 mg) 30-60 min antes "
        "de acostarse. Uso puntual o en viajes con desfase horario.",
        "para_que_sirve": "Regula el ritmo circadiano; puede mejorar la "
        "latencia y la calidad del sueño y facilitar la recuperación "
        "cuando hay déficit de sueño.",
        "cuidados": "Dosis bajas son suficientes (más no es mejor: las "
        "dosis altas producen somnolencia matutina). Precaución con "
        "anticoagulantes, prolongación del QT o sedantes. Regula también "
        "el desfase horario.",
    },
    {
        "categoria": "Regulación del sueño y sistema nervioso",
        "grupo": GRUPO_C,
        "nombre": "L-teanina",
        "posologia": "100-400 mg, 30-60 min antes de dormir o de la "
        "competición.",
        "para_que_sirve": "Promueve un estado de calma sin sedación "
        "profunda; puede reducir la ansiedad somática pre-competición y "
        "facilitar la conciliación del sueño.",
        "cuidados": "Segura y bien tolerada. Puede aumentar el efecto de "
        "la cafeína, no eliminarlo. Interactúa con fármacos para la "
        "presión arterial y con sedantes.",
    },
    {
        "categoria": "Regulación del sueño y sistema nervioso",
        "grupo": GRUPO_C,
        "nombre": "Glicina",
        "posologia": "3 g 30-60 min antes de dormir.",
        "para_que_sirve": "Aminoácido inhibitorio que puede mejorar la "
        "calidad del sueño y la sensación de bienestar, y reducir la "
        "fatiga percibida al día siguiente.",
        "cuidados": "Generalmente segura. Precaución en insuficiencia "
        "renal. Puede interactuar con medicación para la tiroides y con "
        "sedantes.",
    },
    {
        "categoria": "Regulación del sueño y sistema nervioso",
        "grupo": GRUPO_C,
        "nombre": "Ashwagandha (Withania somnifera)",
        "posologia": "300-600 mg/día de extracto estandarizado (KSM-66 o "
        "Sensoril), dividido en 1-2 tomas.",
        "para_que_sirve": "Fitoquímico adaptógeno con evidencia moderada "
        "en reducción del estrés y la ansiedad, y posibles mejoras "
        "ligeras en fuerza y masa muscular.",
        "cuidados": "Interactúa con sedantes, antidiabéticos y "
        "medicamentos tiroideos. Precaución en enfermedades "
        "autoinmunes, embarazo y lactancia. Puede causar somnolencia y "
        "problemas gastrointestinales.",
    },
    # ------------------------------------------------------------------
    # SALUD ARTICULAR Y ANTIINFLAMATORIO
    # ------------------------------------------------------------------
    {
        "categoria": "Salud articular y antiinflamatorio",
        "grupo": GRUPO_A,
        "nombre": "Creatina monohidrato (efecto estructural)",
        "posologia": "3-5 g/día en dosis única, mantenida de forma "
        "continua.",
        "para_que_sirve": "Además de sus efectos sobre fuerza y "
        "rendimiento, aumenta la síntesis de miofibrillas y la "
        "resistencia del músculo, lo que puede reducir el riesgo de "
        "lesiones por sobreuso.",
        "cuidados": "Retención de agua y posible aumento de peso. Debe "
        "usarse de forma sostenida para obtener beneficios "
        "estructurales. Segura en riñones sanos.",
    },
    {
        "categoria": "Salud articular y antiinflamatorio",
        "grupo": GRUPO_B,
        "nombre": "Curcumina (polifenoles de cúrcuma)",
        "posologia": "500-1000 mg/día de curcumina, o 1-2 g/día de "
        "extracto estandarizado al 95% con piperina 5-20 mg, o con "
        "formulación liposomal. Dividir en 2 tomas con comida.",
        "para_que_sirve": "Acción antiinflamatoria y analgésica suave "
        "sobre el dolor articular y muscular, con efecto similar al de "
        "los AINE en estudios de dolor.",
        "cuidados": "Baja biodisponibilidad: usar con piperina (aumenta "
        "la absorción de forma notable) o formulaciones lipídicas. "
        "Interactúa con anticoagulantes y antiplaquetarios (riesgo de "
        "hemorragia). Precaución en obstrucción biliar o cálculos.",
    },
    {
        "categoria": "Salud articular y antiinflamatorio",
        "grupo": GRUPO_B,
        "nombre": "Condroitina y glucosamina",
        "posologia": "Glucosamina sulfato: 1500 mg/día. Condroitina: "
        "800-1200 mg/día. En combinación: 1500 mg de glucosamina + 800 mg "
        "de condroitina durante 8-12 semanas.",
        "para_que_sirve": "Componentes de la matriz del cartílago. Posible "
        "alivio del dolor en osteoartritis de rodilla y reducción de la "
        "pérdida de cartílago a mediano plazo.",
        "cuidados": "Evidencia inconsistente y específica de "
        "osteoartritis: no son suplementos de rendimiento. Precaución en "
        "alergia al camarón (glucosamina) y en pacientes anticoagulados "
        "(condroitina). Interactúan con warfarina (aumentan el INR).",
    },
    {
        "categoria": "Salud articular y antiinflamatorio",
        "grupo": GRUPO_C,
        "nombre": "Omega-3 (EPA + DHA)",
        "posologia": "1-3 g/día de EPA + DHA combinados (no del aceite de "
        "pescado total). Idealmente ratio EPA:DHA mayor a 1.5:1 y bajo "
        "oxidación.",
        "para_que_sirve": "Ácidos grasos poliinsaturados con acción "
        "antiinflamatoria: pueden reducir el dolor muscular pos-ejercicio, "
        "la inflamación post-ejercicio y apoyar la salud articular y "
        "cardiovascular.",
        "cuidados": "Riesgo de efecto anticoagulante a dosis altas. "
        "Verificar la ausencia de oxidación (olor fuerte). Puede "
        "producir eructos con sabor a pescado y reflujo. No sustituye el "
        "consumo de 2 raciones de pescado por semana.",
    },
    {
        "categoria": "Salud articular y antiinflamatorio",
        "grupo": GRUPO_C,
        "nombre": "Colágeno UC-II no desnaturalizado",
        "posologia": "40 mg/día de UC-II con 50 mg de vitamina C.",
        "para_que_sirve": "Estudia la modulación de la respuesta "
        "inmunitaria frente al cartílago, con posibles efectos sobre el "
        "dolor articular.",
        "cuidados": "Evidencia preliminar, basada en estudios pequeños. "
        "Precaución en alergia a proteínas aviares. Interacción con "
        "anticoagulantes por su contenido de vitamina K.",
    },
    # ------------------------------------------------------------------
    # ANTIOXIDANTES
    # ------------------------------------------------------------------
    {
        "categoria": "Antioxidantes",
        "grupo": GRUPO_C,
        "nombre": "Vitamina C",
        "posologia": "75-200 mg/día (no exceder 500 mg/día en la mayoría "
        "de los adultos). Tomarla con carbohidratos 1-2 h antes del "
        "esfuerzo puede aumentar la resistencia.",
        "para_que_sirve": "Antioxidante hidrosoluble; participa en la "
        "síntesis de colágeno y en la función inmune. Reduce el estrés "
        "oxidativo inducido por el ejercicio intenso.",
        "cuidados": "Dosis altas (1 g o más) pueden causar diarrea y "
        "molestias gastrointestinales, y podrían interferir con el "
        "entrenamiento de fuerza. En fumadores o con hemocromatosis, uso "
        "supervisado.",
    },
    {
        "categoria": "Antioxidantes",
        "grupo": GRUPO_C,
        "nombre": "Vitamina E",
        "posologia": "15-30 mg/día (equivalente a la RDA). No se "
        "recomienda la suplementación específica en atletas sin "
        "deficiencia.",
        "para_que_sirve": "Antioxidante liposoluble que protege a las "
        "membranas celulares del daño por radicales libres.",
        "cuidados": "El IOC no recomienda su suplementación rutinaria: "
        "dosis altas (235 mg/día o más) pueden inhibir el entrenamiento "
        "adaptativo al ejercicio y favorecer la peroxidación. Riesgo de "
        "toxicidad por acumulación (hígado).",
    },
    {
        "categoria": "Antioxidantes",
        "grupo": GRUPO_C,
        "nombre": "Selenio",
        "posologia": "55 ug/día (RDA). No suplementar por encima de 400 "
        "ug/día.",
        "para_que_sirve": "Componente de enzimas antioxidantes "
        "(glutatión peroxidasas) y parte del metabolismo de las hormonas "
        "tiroideas.",
        "cuidados": "Margen de seguridad estrecho: la suplementación "
        "innecesaria puede causar selenosis. Interactúa con fármacos "
        "tiroideos y con estatinas. Solo suplementar con déficit "
        "documentado.",
    },
    # ------------------------------------------------------------------
    # SISTEMA INMUNE E INFECCIÓN
    # ------------------------------------------------------------------
    {
        "categoria": "Sistema inmune e infección",
        "grupo": GRUPO_A,
        "nombre": "Probióticos",
        "posologia": "5-10 mil millones de UFC/día, con al menos 2 cepas "
        "y viabilidad garantizada al vencimiento. 2-4 semanas antes de "
        "periodos de alta carga o de viaje.",
        "para_que_sirve": "Puede reducir la incidencia de infecciones "
        "respiratorias y gastrointestinales en atletas con alta carga de "
        "entrenamiento.",
        "cuidados": "El beneficio depende de la cepa: elegir productos "
        "con UFC garantizada y cadena de frío. Precaución en pacientes "
        "inmunodeprimidos. Puede causar gases o distensión abdominal.",
    },
    {
        "categoria": "Sistema inmune e infección",
        "grupo": GRUPO_C,
        "nombre": "Vitamina D",
        "posologia": "1000-2000 UI/día como mantenimiento general; "
        "corrección según niveles (objetivo 30-50 ng/mL). Dosis "
        "fisiológicas hasta 4000 UI/día sin supervisión médica.",
        "para_que_sirve": "Regula el calcio y el fosfato, la función "
        "muscular y la respuesta inmune. Su deficiencia se asocia con "
        "mayor riesgo de lesiones y peor rendimiento.",
        "cuidados": "No suplementar a ciegas: dosificar niveles "
        "sanguíneos (25-OH vitamina D). Toxicidad por hipercalcemia con "
        "dosis altas o acumuladas. Precaución en hiperparatiroidismo y "
        "litiasis.",
    },
    {
        "categoria": "Sistema inmune e infección",
        "grupo": GRUPO_C,
        "nombre": "Zinc",
        "posologia": "8-11 mg/día (RDA). 25-50 mg/día durante 7-14 días "
        "en infecciones respiratorias agudas. No superar 40 mg/día de "
        "forma prolongada.",
        "para_que_sirve": "Involucrado en la función inmune, la síntesis "
        "de proteínas y la división celular. Puede reducir la duración "
        "del resfriado común.",
        "cuidados": "El uso prolongado en dosis altas (40 mg/día o más) "
        "causa deficiencia de cobre y anemia. Reduce la absorción de "
        "hierro y cobre. No usar intranasal a largo plazo (pérdida del "
        "olfato).",
    },
    # ------------------------------------------------------------------
    # RENDIMIENTO EN CALOR Y ALTURA
    # ------------------------------------------------------------------
    {
        "categoria": "Rendimiento en calor y altura",
        "grupo": GRUPO_A,
        "nombre": "Cloruro de sodio en aclimatación a la altura",
        "posologia": "500-700 mg de sodio/h en calor. En aclimatación a la "
        "altura: 4-5 g/día de NaCl bajo supervisión médica.",
        "para_que_sirve": "Favorece la retención de agua y la volemia "
        "plasmática en la aclimatación a la altura, reduciendo los "
        "síntomas del mal de altura y la caída del rendimiento en "
        "altitud.",
        "cuidados": "Hipertensión y retención de líquidos: requiere "
        "seguimiento médico y ajuste de la ingesta de agua. "
        "Contraindicado en insuficiencia renal y en hipertensión "
        "arterial. Monitorizar electrolitos y presión arterial.",
    },
    {
        "categoria": "Rendimiento en calor y altura",
        "grupo": GRUPO_B,
        "nombre": "Cloruro de amonio",
        "posologia": "4-5 g/día de NaCl durante 14 días como parte de un "
        "protocolo de aclimatación, siempre bajo supervisión médica.",
        "para_que_sirve": "Estimula la vía metabólica de la glutamina en "
        "el riñón, aumentando la producción de bicarbonato y facilitando "
        "la aclimatación a la altura.",
        "cuidados": "Precaución en insuficiencia renal o hepática. "
        "Interactúa con los IECAs (aumenta el potasio y reduce el efecto "
        "antihipertensivo). Solo con supervisión médica.",
    },
    {
        "categoria": "Rendimiento en calor y altura",
        "grupo": GRUPO_C,
        "nombre": "Glicerol (hiperhidratación)",
        "posologia": "1-2 g/kg de masa corporal con 1.5-2 L de agua, 2-4 h "
        "antes del esfuerzo en ambiente caluroso.",
        "para_que_sirve": "Aumenta la volemia plasmática y mejora la "
        "termorregulación y el rendimiento en calor.",
        "cuidados": "Puede causar cólicos, náuseas y hiperosmolaridad. "
        "Debe mezclarse con suficiente agua. Precaución en hipertensión, "
        "diabetes y enfermedad renal. Seguir estrictamente el protocolo "
        "de hidratación: riesgo de deshidratación hipernatrémica si no se "
        "ingiere el agua adecuada.",
    },
    {
        "categoria": "Rendimiento en calor y altura",
        "grupo": GRUPO_C,
        "nombre": "Beta-alanina (en ambiente caluroso)",
        "posologia": "4-6.4 g/día, igual que en la categoría de energía y "
        "rendimiento.",
        "para_que_sirve": "Puede preservar la fuerza y reducir la fatiga "
        "muscular en ejercicios mantenidos en calor, donde la "
        "acumulación de H+ es un factor limitante.",
        "cuidados": "Parestesia transitoria. La evidencia específica en "
        "entornos calurosos es limitada. No sustituye a la aclimatación "
        "térmica, que sigue siendo la estrategia de referencia.",
    },
    # ------------------------------------------------------------------
    # SALUD DIGESTIVA
    # ------------------------------------------------------------------
    {
        "categoria": "Salud digestiva",
        "grupo": GRUPO_C,
        "nombre": "Bicarbonato (reflujo gástrico)",
        "posologia": "1-2 g (cucharada pequeña) 30-60 min antes de la "
        "comida.",
        "para_que_sirve": "Neutraliza la acidez gástrica, aliviando el "
        "reflujo y el ardor, lo que puede facilitar la ingesta de volumen "
        "pre-competición.",
        "cuidados": "Puede neutralizar la acidez y alterar la absorción "
        "de medicamentos. No usar como tratamiento crónico del reflujo sin "
        "valoración médica. Interactúa con sales de hierro y con "
        "antifúngicos azoles.",
    },
    {
        "categoria": "Salud digestiva",
        "grupo": GRUPO_C,
        "nombre": "Lactasa (enzima)",
        "posologia": "1 cápsula (3000-9000 U de lactasa) con la primera "
        "bocanada de alimentos con lactosa, según la cantidad ingerida.",
        "para_que_sirve": "Facilita la digestión de la lactosa en "
        "personas con intolerancia, permitiendo tolerar leche y derivados "
        "sin síntomas.",
        "cuidados": "No es necesaria en personas con tolerancia normal. "
        "Precaución en enfermedad celíaca o alergia a la proteína de "
        "leche. Puede reducir la absorción del calcio de la leche al "
        "sustituir productos con lactosa.",
    },
    {
        "categoria": "Salud digestiva",
        "grupo": GRUPO_C,
        "nombre": "Glicina en bebida isotónica",
        "posologia": "Según el protocolo de la bebida isotónica: 300-600 "
        "mg de sodio y 20-30 g de carbohidratos por hora de esfuerzo.",
        "para_que_sirve": "La glicina actúa como amortiguador del pH "
        "gástrico y mejora la absorción de agua y electrolitos en el "
        "intestino.",
        "cuidados": "Debe usarse como complemento de una bebida "
        "isotónica, no como sustituto. Revisar el contenido total de sodio "
        "y azúcares añadidos en la etiqueta. Precaución en hipertensión.",
    },
]


def cargar_catalogo_suplementos(conn):
    """Inserta el catálogo de suplementos si la tabla está vacía."""
    total = conn.execute("SELECT COUNT(*) FROM suplementos").fetchone()[0]
    if total > 0:
        return 0
    for sup in CATALOGO:
        conn.execute(
            "INSERT INTO suplementos "
            "(categoria, grupo, nombre, posologia, para_que_sirve, cuidados) "
            "VALUES (:categoria, :grupo, :nombre, :posologia, :para_que_sirve, "
            ":cuidados)",
            sup,
        )
    return len(CATALOGO)
