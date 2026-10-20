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


if __name__ == "__main__":
    init_db()
    print(f"Base de datos creada: {DB_PATH}")
