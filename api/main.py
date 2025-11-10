# api/main.py
from fastapi import FastAPI, HTTPException, Query, Header
from pydantic import BaseModel
from repo.sqlite_repo import SQLiteRepository
import sqlite3
import os

from domain.service import TurnoService, SlotOcupadoError

app = FastAPI(title="Turnos API")

conn = sqlite3.connect("turnos.db",  check_same_thread = False)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev")


# --- wiring (singleton simple) ---
_repo = SQLiteRepository(conn)
_service = TurnoService(_repo)

class ReservaIn(BaseModel):
    nombre_cliente: str
    telefono_cliente: str
    fecha_turno: str  # YYYY-MM-DD
    hora_turno: str   # HH:MM
    servicio: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/disponibilidad")
async def disponibilidad(
    fecha: str = Query(..., description="YYYY-MM-DD"),
    servicio: str | None = Query(None)
):
    try:
        return _service.get_disponibilidad(fecha=fecha, servicio=servicio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/reservar")
async def reservar(payload: ReservaIn):
    try:
        turno = _service.reservar(payload.model_dump())
        return {"status": "reservado", "turno": turno.model_dump()}
    except SlotOcupadoError:
        raise HTTPException(status_code=409, detail="ocupado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/admin/reset")
async def admin_reset(
    mode: str = Query("truncate", pattern="^(truncate|drop)$"),
    token: str | None = Header(None, alias="X-Admin-Token"),
):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    if mode == "drop":
        _repo.reset(drop=True)
        return {"ok": True, "mode": "drop", "deleted": 0}
    else:
        deleted = _repo.reset(drop=False)
        return {"ok": True, "mode": "truncate", "deleted": deleted}