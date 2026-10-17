import json
import sqlite3
from pathlib import Path
DB_PATH = Path(__file__).with_name("Nutrición_deportiva.db")

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


if __name__ == "__main__":
    init_db()
    print(f"Base de datos creada: {DB_PATH}")
