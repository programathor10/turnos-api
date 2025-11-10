# repo/sqlite_repo.py
# Repositorio SQLite para el sistema de turnos

import sqlite3
from domain.interfaces import ITurnoRepository


class SQLiteRepository(ITurnoRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

        cursor = self.conn.cursor()
        # Si la tabla no existe, la crea con TODAS las columnas (incluida contacto_id).
        # Si ya existe (aunque con otro esquema), SQLite NO la toca y no falla.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turnos(
                user_id     TEXT,
                contacto_id TEXT,
                updated_at  TEXT,
                fecha       TEXT,
                hora        TEXT,
                servicio    TEXT,
                estado      TEXT,
                UNIQUE(contacto_id,fecha, hora)
            )
        """)
        self.conn.commit()

    def get_turnos_ocupados(self, fecha: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT DISTINCT hora FROM turnos WHERE fecha = ? ORDER BY hora",
            (fecha,)
        )
        resultados = cursor.fetchall()
        horas_ocupadas = [fila[0] for fila in resultados]
        return horas_ocupadas

    def existe_turno(self, fecha: str, hora: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM turnos WHERE fecha = ? AND hora = ? LIMIT 1",
            (fecha, hora)
        )
        resultado = cursor.fetchone()
        return resultado is not None  # True si existe, False si no

    def save_turno(self, turno_data: dict):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO turnos
                (user_id, contacto_id, fecha, hora, servicio, estado, updated_at)
            VALUES
                (?,       ?,           ?,     ?,    ?,        ?,      ?)
            """,
            (
                # user_id: podés usar nombre, teléfono, o combinación
                turno_data.get("nombre_cliente"),
                turno_data.get("telefono_cliente"),
                turno_data["fecha_turno"],
                turno_data["hora_turno"],
                turno_data["servicio"].strip().lower(),
                turno_data["estado"],
                turno_data.get("updated_at"),  # puede ir None
            )
        )
        self.conn.commit()
    
    def reset(self, drop: bool = False) -> int:
    
    # Si drop=False -> borra filas (DELETE) y retorna cantidad.
    # Si drop=True  -> borra tabla (DROP TABLE) y la recrea.
        cursor = self.conn.cursor()
        if drop:
            cursor.execute("DROP TABLE IF EXISTS turnos;")
            self.conn.commit()

            # Recrea la tabla igual que en __init__
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turnos(
                    user_id TEXT,
                    contacto_id TEXT,
                    updated_at TEXT,
                    fecha TEXT,
                    hora TEXT,
                    servicio TEXT,
                    estado TEXT,
                    UNIQUE(fecha, hora)
                )
            """)
            self.conn.commit()
            return 0
        else:
            cursor.execute("DELETE FROM turnos;")
            count = cursor.rowcount if cursor.rowcount else 0
            self.conn.commit()
            return count

