import json
import sqlite3
from pathlib import Path
DB_PATH = Path(__file__).with_name("Nutrición_deportiva.db")
MET_CSV_PATH = Path(__file__).with_name("mets.csv")

CAMPOS = [
    "deporte",
    "fecha",
    "nombre",
    "dob",
    "fecha_nacimiento",
    "direccion",
    "genero",
    "telefono",
    "email",
    "facebook",
    "gimnasio",
    "coach",
    "proposito",
]

CAMPOS_ANTROPOMETRIA = [
    "fecha",
    "peso",
    "altura",
    "sum_pliegues",
    "grasa",
    "metodo",
    "clasificacion_peso",
    "masa_muscular",
    "problemas_soluciones",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        columnas = ",\n    ".join(f"{c} TEXT" for c in CAMPOS)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                {columnas},
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        existentes = [
            r[1] for r in conn.execute("PRAGMA table_info(pacientes)").fetchall()
        ]
        if "codigo" not in existentes:
            conn.execute("ALTER TABLE pacientes ADD COLUMN codigo TEXT")
        for columna in CAMPOS:
            if columna not in existentes:
                conn.execute(f"ALTER TABLE pacientes ADD COLUMN {columna} TEXT")

        conn.execute(
            "UPDATE pacientes "
            "SET codigo = 'PAC-' || printf('%04d', id) "
            "WHERE codigo IS NULL OR codigo = ''"
        )

        columnas_antro = ",\n    ".join(
            f"{c} TEXT" for c in CAMPOS_ANTROPOMETRIA
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS antropometria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                {columnas_antro},
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS perfil_isak (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                datos TEXT,
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS smae_alimentos (
                id_alimento INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo TEXT,
                alimento TEXT,
                cantidad_sugerida REAL,
                unidad TEXT,
                peso_bruto_g REAL,
                peso_neto_g REAL,
                energia_kcal REAL,
                proteina_g REAL,
                lipidos_g REAL,
                hc_g REAL,
                fibra_g REAL,
                vitamina_a_ug REAL,
                vitamina_c_mg REAL,
                acido_folico_ug REAL,
                hierro_mg REAL,
                potasio_mg REAL,
                calcio_mg REAL,
                sodio_mg REAL,
                azucar_g REAL,
                indice_glucemico REAL,
                carga_glucemica REAL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS r24h (
                id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                tiempo_comida TEXT,
                id_alimento INTEGER,
                alimento TEXT,
                grupo TEXT,
                cantidad_equivalentes REAL,
                energia_kcal REAL,
                proteina_g REAL,
                lipidos_g REAL,
                hc_g REAL,
                fibra_g REAL,
                vitamina_a_ug REAL,
                vitamina_c_mg REAL,
                acido_folico_ug REAL,
                hierro_mg REAL,
                potasio_mg REAL,
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS formulas (
                id_calculo INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                peso REAL,
                edad REAL,
                sexo TEXT,
                pal REAL,
                horas_no_ejercicio REAL,
                categoria TEXT,
                actividad TEXT,
                mets REAL,
                horas_ejercicio REAL,
                bmr REAL,
                rango_edad TEXT,
                gee REAL,
                eee REAL,
                tee REAL,
                ea REAL,
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS equivalentes (
                id_distribucion INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                tee REAL,
                peso REAL,
                pct_carb REAL,
                pct_prot REAL,
                pct_grasa REAL,
                total_kcal REAL,
                total_prot REAL,
                total_lip REAL,
                total_hc REAL,
                detalle TEXT,
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS menus (
                id_menu INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER UNIQUE REFERENCES pacientes(id),
                detalle TEXT,
                creado_en TEXT DEFAULT (datetime('now', 'localtime')),
                actualizado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS suplementos (
                id_suplemento INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT,
                grupo TEXT,
                nombre TEXT,
                posologia TEXT,
                para_que_sirve TEXT,
                cuidados TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS suplementos_paciente (
                id_seleccion INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                id_suplemento INTEGER REFERENCES suplementos(id_suplemento),
                nombre TEXT,
                categoria TEXT,
                posologia TEXT,
                momento TEXT,
                dosis TEXT,
                notas TEXT,
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS antecedentes (
                id_antecedentes INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER UNIQUE REFERENCES pacientes(id),
                pat_familiares TEXT,
                pat_personales TEXT,
                pat_alergia_alimentaria TEXT,
                pat_quirurgicos TEXT,
                nopat_tabaco TEXT,
                nopat_alcohol TEXT,
                nopat_drogas TEXT,
                nopat_cafe TEXT,
                nopat_medicamentos TEXT,
                nopat_actividad_fisica TEXT,
                nopat_problemas_intestinales TEXT,
                creado_en TEXT DEFAULT (datetime('now', 'localtime')),
                actualizado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        columnas_antecedentes = [
            r[1]
            for r in conn.execute("PRAGMA table_info(antecedentes)").fetchall()
        ]
        for columna in ANTECEDENTES_CAMPOS:
            if columna not in columnas_antecedentes:
                conn.execute(f"ALTER TABLE antecedentes ADD COLUMN {columna} TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS estiramientos (
                id_estiramiento INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo TEXT,
                numero INTEGER,
                nombre TEXT,
                descripcion TEXT,
                musculos TEXT,
                variantes TEXT,
                observaciones TEXT,
                atencion TEXT,
                rotulos TEXT,
                pagina_original INTEGER,
                imagen TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS estiramientos_paciente (
                id_seleccion INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                id_estiramiento INTEGER REFERENCES estiramientos(id_estiramiento),
                grupo TEXT,
                nombre TEXT,
                momento TEXT,
                duracion TEXT,
                notas TEXT,
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rutinas_ejercicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo TEXT,
                num TEXT,
                nombre TEXT,
                equipo TEXT,
                imagen_nombre TEXT,
                imagen_blob BLOB,
                descripcion TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rutinas_paciente (
                id_rutina INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER REFERENCES pacientes(id),
                grupo TEXT,
                num TEXT,
                nombre TEXT,
                equipo TEXT,
                series TEXT,
                repeticiones TEXT,
                descanso_rep TEXT,
                descanso_series TEXT,
                peso TEXT,
                orden INTEGER,
                notas TEXT,
                creado_en TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        try:
            from suplementos_data import cargar_catalogo_suplementos

            cargar_catalogo_suplementos(conn)
        except Exception:
            pass

        try:
            from estiramientos_data import cargar_catalogo_estiramientos

            cargar_catalogo_estiramientos(conn)
        except Exception:
            pass



def generar_codigo(id_paciente):
    return f"PAC-{id_paciente:04d}"


def guardar_paciente(datos: dict):
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO pacientes ({', '.join(CAMPOS)}) "
            f"VALUES ({', '.join(':' + c for c in CAMPOS)})",
            {c: datos.get(c, "") for c in CAMPOS},
        )
        nuevo_id = cur.lastrowid
        conn.execute(
            "UPDATE pacientes SET codigo = ? WHERE id = ?",
            (generar_codigo(nuevo_id), nuevo_id),
        )
        return nuevo_id


def actualizar_paciente(id_paciente, datos: dict):
    asignaciones = ", ".join(f"{c} = :{c}" for c in CAMPOS)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE pacientes SET {asignaciones} WHERE id = :id_paciente",
            {**{c: datos.get(c, "") for c in CAMPOS}, "id_paciente": id_paciente},
        )


def obtener_paciente(id_paciente):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            "SELECT * FROM pacientes WHERE id = ?", (id_paciente,)
        ).fetchone()
        return dict(fila) if fila else None


def guardar_antropometria(datos: dict, paciente_id=None):
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO antropometria (paciente_id, {', '.join(CAMPOS_ANTROPOMETRIA)}) "
            f"VALUES (:paciente_id, {', '.join(':' + c for c in CAMPOS_ANTROPOMETRIA)})",
            {
                "paciente_id": paciente_id,
                **{c: datos.get(c, "") for c in CAMPOS_ANTROPOMETRIA},
            },
        )
        return cur.lastrowid


def obtener_pacientes():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM pacientes ORDER BY id DESC")
        return [dict(fila) for fila in cur.fetchall()]


def obtener_antropometria():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM antropometria ORDER BY id DESC")
        return cur.fetchall()


def guardar_perfil_isak(paciente_id, datos: dict):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO perfil_isak (paciente_id, datos) VALUES (?, ?)",
            (paciente_id, json.dumps(datos, ensure_ascii=False)),
        )
        return cur.lastrowid


def obtener_perfil_isak(paciente_id=None):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if paciente_id is None:
            cur = conn.execute(
                "SELECT * FROM perfil_isak ORDER BY id DESC"
            )
        else:
            cur = conn.execute(
                "SELECT * FROM perfil_isak WHERE paciente_id = ? ORDER BY id DESC",
                (paciente_id,),
            )
        return cur.fetchall()


def recrear_smae_alimentos():
    with get_connection() as conn:
        conn.execute("DELETE FROM smae_alimentos")
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name = 'smae_alimentos'"
        )


def contar_smae_alimentos():
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM smae_alimentos"
        ).fetchone()[0]


def get_smae_grupos():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT grupo, COUNT(*) AS total FROM smae_alimentos "
            "GROUP BY grupo ORDER BY MIN(id_alimento)"
        )
        return [dict(f) for f in cur.fetchall()]


def get_smae_alimentos_por_grupo(grupo):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM smae_alimentos WHERE grupo = ? ORDER BY alimento",
            (grupo,),
        )
        return [dict(f) for f in cur.fetchall()]


def get_smae_alimento(id_alimento):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            "SELECT * FROM smae_alimentos WHERE id_alimento = ?",
            (id_alimento,),
        ).fetchone()
        return dict(fila) if fila else None


def get_smae_buscar(texto):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM smae_alimentos WHERE alimento LIKE ? "
            "ORDER BY grupo, alimento",
            (f"%{texto}%",),
        )
        return [dict(f) for f in cur.fetchall()]


def insert_r24h(data):
    campos = [
        "paciente_id",
        "tiempo_comida",
        "id_alimento",
        "alimento",
        "grupo",
        "cantidad_equivalentes",
        "energia_kcal",
        "proteina_g",
        "lipidos_g",
        "hc_g",
        "fibra_g",
        "vitamina_a_ug",
        "vitamina_c_mg",
        "acido_folico_ug",
        "hierro_mg",
        "potasio_mg",
    ]
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO r24h ({', '.join(campos)}) "
            f"VALUES ({', '.join(':' + c for c in campos)})",
            {c: data.get(c, 0) for c in campos},
        )
        return cur.lastrowid


def get_r24h(paciente_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM r24h WHERE paciente_id = ? ORDER BY id_registro",
            (paciente_id,),
        )
        return [dict(f) for f in cur.fetchall()]


def get_r24h_por_comida(paciente_id, tiempo_comida):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM r24h WHERE paciente_id = ? AND tiempo_comida = ? "
            "ORDER BY id_registro",
            (paciente_id, tiempo_comida),
        )
        return [dict(f) for f in cur.fetchall()]


def delete_r24h(id_registro):
    with get_connection() as conn:
        conn.execute("DELETE FROM r24h WHERE id_registro = ?", (id_registro,))


def delete_r24h_paciente(paciente_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM r24h WHERE paciente_id = ?", (paciente_id,))


FORMULAS_CAMPOS = [
    "paciente_id",
    "peso",
    "edad",
    "sexo",
    "pal",
    "horas_no_ejercicio",
    "categoria",
    "actividad",
    "mets",
    "horas_ejercicio",
    "bmr",
    "rango_edad",
    "gee",
    "eee",
    "tee",
    "ea",
]


def insert_formulas(data):
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO formulas ({', '.join(FORMULAS_CAMPOS)}) "
            f"VALUES ({', '.join(':' + c for c in FORMULAS_CAMPOS)})",
            {c: data.get(c) for c in FORMULAS_CAMPOS},
        )
        return cur.lastrowid


def get_formulas(paciente_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM formulas WHERE paciente_id = ? "
            "ORDER BY id_calculo DESC",
            (paciente_id,),
        )
        return [dict(f) for f in cur.fetchall()]


def delete_formulas_paciente(paciente_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM formulas WHERE paciente_id = ?", (paciente_id,))


EQUIVALENTES_CAMPOS = [
    "paciente_id",
    "tee",
    "peso",
    "pct_carb",
    "pct_prot",
    "pct_grasa",
    "total_kcal",
    "total_prot",
    "total_lip",
    "total_hc",
    "detalle",
]


def insert_equivalentes(data):
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO equivalentes ({', '.join(EQUIVALENTES_CAMPOS)}) "
            f"VALUES ({', '.join(':' + c for c in EQUIVALENTES_CAMPOS)})",
            {c: data.get(c) for c in EQUIVALENTES_CAMPOS},
        )
        return cur.lastrowid


def get_equivalentes(paciente_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM equivalentes WHERE paciente_id = ? "
            "ORDER BY id_distribucion DESC",
            (paciente_id,),
        )
        return [dict(f) for f in cur.fetchall()]


def delete_equivalentes_paciente(paciente_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM equivalentes WHERE paciente_id = ?", (paciente_id,)
        )


def guardar_menu(paciente_id, detalle):
    """Upsert del menú (JSON) de un paciente."""
    with get_connection() as conn:
        existe = conn.execute(
            "SELECT id_menu FROM menus WHERE paciente_id = ?", (paciente_id,)
        ).fetchone()
        if existe:
            conn.execute(
                "UPDATE menus SET detalle = ?, "
                "actualizado_en = datetime('now', 'localtime') "
                "WHERE paciente_id = ?",
                (detalle, paciente_id),
            )
        else:
            conn.execute(
                "INSERT INTO menus (paciente_id, detalle) VALUES (?, ?)",
                (paciente_id, detalle),
            )


def get_menu(paciente_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            "SELECT * FROM menus WHERE paciente_id = ?", (paciente_id,)
        ).fetchone()
        return dict(fila) if fila else None


def delete_menu_paciente(paciente_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM menus WHERE paciente_id = ?", (paciente_id,))


def cargar_mets():
    """Lee mets.csv (Compendio 2011) y devuelve lista de dicts."""
    import csv

    if not MET_CSV_PATH.exists():
        return []
    with MET_CSV_PATH.open("r", encoding="utf-8") as f:
        return [
            {
                "codigo": fila["codigo"],
                "mets": float(fila["mets"]),
                "categoria": fila["categoria"],
                "actividad": fila["actividad"],
            }
            for fila in csv.DictReader(f)
        ]


def get_mets_categorias():
    categorias = []
    for m in cargar_mets():
        if m["categoria"] not in categorias:
            categorias.append(m["categoria"])
    return sorted(categorias)


def get_mets_por_categoria(categoria):
    return [m for m in cargar_mets() if m["categoria"] == categoria]


# ----------------------------------------------------------------------
# Suplementos
# ----------------------------------------------------------------------
def get_suplementos_categorias():
    with get_connection() as conn:
        filas = conn.execute(
            "SELECT DISTINCT categoria FROM suplementos ORDER BY categoria"
        ).fetchall()
    return [f[0] for f in filas]


def get_suplementos_grupos():
    with get_connection() as conn:
        filas = conn.execute(
            "SELECT DISTINCT grupo FROM suplementos ORDER BY grupo"
        ).fetchall()
    return [f[0] for f in filas]


def get_suplementos(categoria=None, grupo=None):
    sql = "SELECT * FROM suplementos WHERE 1=1"
    params = []
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    if grupo:
        sql += " AND grupo = ?"
        params.append(grupo)
    sql += " ORDER BY categoria, nombre"
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute(sql, params).fetchall()
    return [dict(f) for f in filas]


def get_suplemento(id_suplemento):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            "SELECT * FROM suplementos WHERE id_suplemento = ?",
            (id_suplemento,),
        ).fetchone()
    return dict(fila) if fila else None


def insert_suplemento_paciente(data):
    campos = [
        "paciente_id",
        "id_suplemento",
        "nombre",
        "categoria",
        "posologia",
        "momento",
        "dosis",
        "notas",
    ]
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO suplementos_paciente ({', '.join(campos)}) "
            f"VALUES ({', '.join(':' + c for c in campos)})",
            {c: data.get(c) for c in campos},
        )
        return cur.lastrowid


def get_suplementos_paciente(paciente_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute(
            "SELECT * FROM suplementos_paciente WHERE paciente_id = ? "
            "ORDER BY id_seleccion",
            (paciente_id,),
        ).fetchall()
    return [dict(f) for f in filas]


def delete_suplemento_paciente(id_seleccion):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM suplementos_paciente WHERE id_seleccion = ?",
            (id_seleccion,),
        )


def delete_suplementos_paciente(paciente_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM suplementos_paciente WHERE paciente_id = ?",
            (paciente_id,),
        )


def contar_suplementos():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM suplementos").fetchone()[0]


# ----------------------------------------------------------------------
# Rutinas (catálogo de ejercicios)
# ----------------------------------------------------------------------
def get_rutinas_ejercicios(grupo="hombros"):
    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        filas = conn.execute(
            "SELECT * FROM rutinas_ejercicios WHERE grupo = ? ORDER BY num",
            (grupo,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(f) for f in filas]


def contar_rutinas_ejercicios(grupo="hombros"):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM rutinas_ejercicios WHERE grupo = ?", (grupo,)
        ).fetchone()[0]
    finally:
        conn.close()


def get_rutinas_paciente(paciente_id, grupo=None):
    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM rutinas_paciente WHERE paciente_id = ?"
        parametros = [paciente_id]
        if grupo:
            sql += " AND grupo = ?"
            parametros.append(grupo)
        sql += " ORDER BY orden, id_rutina"
        filas = conn.execute(sql, parametros).fetchall()
    finally:
        conn.close()
    return [dict(f) for f in filas]


def contar_rutinas_paciente(paciente_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM rutinas_paciente WHERE paciente_id = ?",
            (paciente_id,),
        ).fetchone()[0]
    finally:
        conn.close()


def insert_rutina_paciente(datos):
    conn = get_connection()
    try:
        orden = conn.execute(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM rutinas_paciente WHERE paciente_id = ?",
            (datos["paciente_id"],),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO rutinas_paciente (paciente_id, grupo, num, nombre, equipo, "
            "series, repeticiones, descanso_rep, descanso_series, peso, orden, notas) "
            "VALUES (:paciente_id, :grupo, :num, :nombre, :equipo, :series, "
            ":repeticiones, :descanso_rep, :descanso_series, :peso, :orden, :notas)",
            {
                "paciente_id": datos["paciente_id"],
                "grupo": datos.get("grupo"),
                "num": datos.get("num"),
                "nombre": datos.get("nombre"),
                "equipo": datos.get("equipo"),
                "series": datos.get("series"),
                "repeticiones": datos.get("repeticiones"),
                "descanso_rep": datos.get("descanso_rep"),
                "descanso_series": datos.get("descanso_series"),
                "peso": datos.get("peso"),
                "orden": orden,
                "notas": datos.get("notas"),
            },
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_rutina_paciente(id_rutina):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM rutinas_paciente WHERE id_rutina = ?", (id_rutina,))
        conn.commit()
    finally:
        conn.close()


def delete_rutinas_paciente(paciente_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM rutinas_paciente WHERE paciente_id = ?", (paciente_id,))
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Estiramientos (catálogo + selección por paciente)
# ----------------------------------------------------------------------
def get_estiramientos_grupos():
    with get_connection() as conn:
        filas = conn.execute(
            "SELECT grupo, MIN(numero) as m FROM estiramientos "
            "GROUP BY grupo ORDER BY m"
        ).fetchall()
    return [f[0] for f in filas]


def get_estiramientos(grupo=None):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if grupo:
            filas = conn.execute(
                "SELECT * FROM estiramientos WHERE grupo = ? ORDER BY numero",
                (grupo,),
            ).fetchall()
        else:
            filas = conn.execute(
                "SELECT * FROM estiramientos ORDER BY numero"
            ).fetchall()
    return [dict(f) for f in filas]


def get_estiramiento(id_estiramiento):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            "SELECT * FROM estiramientos WHERE id_estiramiento = ?",
            (id_estiramiento,),
        ).fetchone()
    return dict(fila) if fila else None


def insert_estiramiento_paciente(data):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO estiramientos_paciente "
            "(paciente_id, id_estiramiento, grupo, nombre, momento, duracion, "
            "notas) VALUES (:paciente_id, :id_estiramiento, :grupo, :nombre, "
            ":momento, :duracion, :notas)",
            data,
        )
        return cur.lastrowid


def get_estiramientos_paciente(paciente_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute(
            "SELECT e.*, s.id_seleccion, s.momento, s.duracion, s.notas "
            "FROM estiramientos_paciente s "
            "LEFT JOIN estiramientos e "
            "ON e.id_estiramiento = s.id_estiramiento "
            "WHERE s.paciente_id = ? ORDER BY s.id_seleccion",
            (paciente_id,),
        ).fetchall()
    return [dict(f) for f in filas]


def delete_estiramiento_paciente(id_seleccion):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM estiramientos_paciente WHERE id_seleccion = ?",
            (id_seleccion,),
        )


def delete_estiramientos_paciente(paciente_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM estiramientos_paciente WHERE paciente_id = ?",
            (paciente_id,),
        )


def contar_estiramientos():
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM estiramientos").fetchone()[0]


# ----------------------------------------------------------------------
# Antecedentes (patológicos y no patológicos)
# ----------------------------------------------------------------------
ANTECEDENTES_CAMPOS = [
    "pat_familiares",
    "pat_personales",
    "pat_alergia_alimentaria",
    "pat_quirurgicos",
    "nopat_tabaco",
    "nopat_alcohol",
    "nopat_drogas",
    "nopat_cafe",
    "nopat_medicamentos",
    "nopat_actividad_fisica",
    "nopat_problemas_intestinales",
]


def guardar_antecedentes(paciente_id, datos: dict):
    """Upsert de los antecedentes patológicos y no patológicos de un paciente."""
    with get_connection() as conn:
        existe = conn.execute(
            "SELECT id_antecedentes FROM antecedentes WHERE paciente_id = ?",
            (paciente_id,),
        ).fetchone()
        valores = {c: datos.get(c, "") for c in ANTECEDENTES_CAMPOS}
        if existe:
            asignaciones = ", ".join(f"{c} = :{c}" for c in ANTECEDENTES_CAMPOS)
            conn.execute(
                f"UPDATE antecedentes SET {asignaciones}, "
                "actualizado_en = datetime('now', 'localtime') "
                "WHERE paciente_id = :paciente_id",
                {**valores, "paciente_id": paciente_id},
            )
        else:
            columnas = ", ".join(["paciente_id"] + ANTECEDENTES_CAMPOS)
            marcas = ", ".join([":paciente_id"] + [f":{c}" for c in ANTECEDENTES_CAMPOS])
            conn.execute(
                f"INSERT INTO antecedentes ({columnas}) VALUES ({marcas})",
                {**valores, "paciente_id": paciente_id},
            )


def get_antecedentes(paciente_id):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        fila = conn.execute(
            "SELECT * FROM antecedentes WHERE paciente_id = ?", (paciente_id,)
        ).fetchone()
    return dict(fila) if fila else None


def delete_antecedentes_paciente(paciente_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM antecedentes WHERE paciente_id = ?", (paciente_id,)
        )


if __name__ == "__main__":
    init_db()
    print(f"Base de datos creada: {DB_PATH}")
