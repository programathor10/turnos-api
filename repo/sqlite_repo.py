# repo/sqlite_repo.py
# Repositorio SQLite para el sistema de turnos

import sqlite3
from typing import Any, Dict, List, Optional
from domain.interfaces import ITurnoRepository


_ALLOWED_UPDATE_FIELDS = {
    "user_id",
    "contacto_id",
    "updated_at",
    "fecha",
    "hora",
    "servicio",
    "estado",
}


class SQLiteRepository(ITurnoRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._create_schema()

    # ---------------------------
    # Esquema
    # ---------------------------
    def _create_schema(self) -> None:
        """
        Crea la tabla si no existe. Mantener el UNIQUE consistente acá y en reset(drop=True).
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS turnos(
                user_id     TEXT,
                contacto_id TEXT,
                updated_at  TEXT,
                fecha       TEXT,
                hora        TEXT,
                servicio    TEXT,
                estado      TEXT,
                -- Para evitar doble reserva por mismo contacto en mismo slot
                UNIQUE(contacto_id, fecha, hora)
            )
            """
        )
        self.conn.commit()

    # ---------------------------
    # Lecturas auxiliares
    # ---------------------------
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convierte una fila con rowid a dict.
        Se asume SELECT con "rowid AS id, user_id, contacto_id, updated_at, fecha, hora, servicio, estado"
        """
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "contacto_id": row["contacto_id"],
            "updated_at": row["updated_at"],
            "fecha": row["fecha"],
            "hora": row["hora"],
            "servicio": row["servicio"],
            "estado": row["estado"],
        }

    # ---------------------------
    # Consultas de disponibilidad
    # ---------------------------
    def get_turnos_ocupados(self, fecha: str) -> List[str]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT DISTINCT hora FROM turnos WHERE fecha = ? ORDER BY hora",
            (fecha,),
        )
        resultados = cur.fetchall()
        return [fila[0] for fila in resultados]

    def existe_turno(self, fecha: str, hora: str) -> bool:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM turnos WHERE fecha = ? AND hora = ? LIMIT 1",
            (fecha, hora),
        )
        return cur.fetchone() is not None

    def existe_turno_en(
        self, fecha: str, hora: str, excluir_id: Optional[int] = None
    ) -> bool:
        """
        Igual a existe_turno, pero permite excluir un rowid (útil al PATCH para no chocar consigo mismo).
        """
        cur = self.conn.cursor()
        if excluir_id is None:
            cur.execute(
                "SELECT 1 FROM turnos WHERE fecha = ? AND hora = ? LIMIT 1",
                (fecha, hora),
            )
        else:
            cur.execute(
                "SELECT 1 FROM turnos WHERE fecha = ? AND hora = ? AND rowid != ? LIMIT 1",
                (fecha, hora, excluir_id),
            )
        return cur.fetchone() is not None

    # ---------------------------
    # CRUD
    # ---------------------------
    def save_turno(self, turno_data: Dict[str, Any]) -> int:
        """
        Inserta un turno y retorna el rowid asignado (para que el service genere el 'ticket').
        Espera keys: nombre_cliente, telefono_cliente, fecha_turno, hora_turno, servicio, estado, updated_at(opc).
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO turnos
                (user_id, contacto_id, updated_at, fecha, hora, servicio, estado)
            VALUES
                (?,       ?,           ?,          ?,     ?,    ?,        ?)
            """,
            (
                turno_data.get("nombre_cliente"),
                turno_data.get("telefono_cliente"),
                turno_data.get("updated_at"),
                turno_data["fecha_turno"],
                turno_data["hora_turno"],
                (turno_data["servicio"] or "").strip().lower(),
                turno_data["estado"],
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_turno_by_rowid(self, rowid: int) -> Optional[Dict[str, Any]]:
        """
        Devuelve el turno (incluye id=rowid) o None si no existe.
        """
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                rowid AS id,
                user_id, contacto_id, updated_at, fecha, hora, servicio, estado
            FROM turnos
            WHERE rowid = ?
            """,
            (rowid,),
        )
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def delete_turno_by_rowid(self, rowid: int) -> bool:
        """
        Borra una fila por rowid. Retorna True si afectó 1 fila.
        """
        cur = self.conn.cursor()
        cur.execute("DELETE FROM turnos WHERE rowid = ?", (rowid,))
        self.conn.commit()
        return (cur.rowcount or 0) == 1

    def update_turno_by_rowid(
        self, rowid: int, cambios: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza campos permitidos y retorna el turno actualizado.
        Si no hay campos válidos en 'cambios', no hace nada y devuelve el actual.
        Retorna None si el rowid no existe.
        """
        if not cambios:
            return self.get_turno_by_rowid(rowid)

        # Filtrar solo campos permitidos
        to_set: Dict[str, Any] = {}
        for k, v in cambios.items():
            if k in _ALLOWED_UPDATE_FIELDS:
                # Normalización simple
                if k == "servicio" and isinstance(v, str):
                    v = v.strip().lower()
                to_set[k] = v

        # Nada válido para actualizar
        if not to_set:
            return self.get_turno_by_rowid(rowid)

        # Armar UPDATE dinámico
        campos = ", ".join(f"{k} = ?" for k in to_set.keys())
        valores = list(to_set.values())
        valores.append(rowid)  # WHERE rowid = ?

        cur = self.conn.cursor()
        cur.execute(f"UPDATE turnos SET {campos} WHERE rowid = ?", valores)
        self.conn.commit()

        if (cur.rowcount or 0) != 1:
            return None

        return self.get_turno_by_rowid(rowid)

    def list_by_contact(self, contacto_id: str) -> List[Dict[str, Any]]:
        """
        Lista turnos por contacto (p.ej., teléfono). Útil para 'mis turnos' en Telegram.
        """
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                rowid AS id,
                user_id, contacto_id, updated_at, fecha, hora, servicio, estado
            FROM turnos
            WHERE contacto_id = ?
            ORDER BY fecha, hora
            """,
            (contacto_id,),
        )
        rows = cur.fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ---------------------------
    # Reset (desarrollo)
    # ---------------------------
    def reset(self, drop: bool = False) -> int:
        """
        Si drop=False -> borra filas (DELETE) y retorna cantidad.
        Si drop=True  -> borra tabla (DROP TABLE) y la recrea.
        """
        cur = self.conn.cursor()
        if drop:
            cur.execute("DROP TABLE IF EXISTS turnos;")
            self.conn.commit()
            self._create_schema()
            return 0

        cur.execute("DELETE FROM turnos;")
        count = cur.rowcount or 0
        self.conn.commit()
        return count
