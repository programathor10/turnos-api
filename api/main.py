# api/main.py
from typing import Optional, Any, Dict

import os
import sqlite3

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Header,
    Path,
    Request,
)
from pydantic import BaseModel, Field
import httpx

from repo.sqlite_repo import SQLiteRepository
from domain.service import TurnoService, SlotOcupadoError

# ----------------- Configuración básica -----------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN no está definido en el .env")

if not WEBHOOK_SECRET:
    raise RuntimeError("WEBHOOK_SECRET no está definido en el .env")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI(title="Turnos API")

# Conexión SQLite (thread-safe para dev)
conn = sqlite3.connect("turnos.db", check_same_thread=False)

# --- wiring (singleton simple) ---
_repo = SQLiteRepository(conn)
_service = TurnoService(_repo)


# ----------------- Modelos de entrada -----------------

class ReservaIn(BaseModel):
    nombre_cliente: str
    telefono_cliente: str
    fecha_turno: str  # YYYY-MM-DD
    hora_turno: str   # HH:MM
    servicio: str
    estado: str = "reservado"  # valor por defecto útil


class TurnoPatchIn(BaseModel):
    # Todos opcionales: PATCH actualiza sólo lo que venga
    fecha: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    hora: Optional[str] = Field(default=None, description="HH:MM")
    servicio: Optional[str] = None
    estado: Optional[str] = None
    user_id: Optional[str] = None
    contacto_id: Optional[str] = None
    updated_at: Optional[str] = None


# ----------------- Endpoints base -----------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/disponibilidad")
async def disponibilidad(
    fecha: str = Query(..., description="YYYY-MM-DD"),
    servicio: Optional[str] = Query(None),
):
    try:
        return _service.get_disponibilidad(fecha=fecha, servicio=servicio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/reservar")
async def reservar(payload: ReservaIn):
    """
    Crea un turno. Ahora devuelve también id y ticket si el service lo provee.
    """
    try:
        result = _service.reservar(payload.model_dump())

        # Soporta ambos retornos mientras migrás el service:
        # - dict con {"id","ticket","turno": {...}}
        # - modelo Pydantic Turno (legacy)
        if isinstance(result, dict) and ("ticket" in result or "id" in result):
            # Forma nueva (recomendada)
            return {"status": "reservado", **result}
        else:
            # Forma legacy para no romperte mientras migrás
            turno_dict = getattr(result, "model_dump", lambda: result)()
            return {"status": "reservado", "turno": turno_dict}

    except SlotOcupadoError:
        raise HTTPException(status_code=409, detail="ocupado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------- Admin -----------------

@app.post("/admin/reset")
async def admin_reset(
    mode: str = Query("truncate", pattern="^(truncate|drop)$"),
    token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    if mode == "drop":
        _repo.reset(drop=True)
        return {"ok": True, "mode": "drop", "deleted": 0}
    else:
        deleted = _repo.reset(drop=False)
        return {"ok": True, "mode": "truncate", "deleted": deleted}


# ============================================================
#           Endpoints por TICKET (telegram-friendly)
# ============================================================

@app.get("/turnos/ticket/{ticket}")
async def get_por_ticket(ticket: str = Path(..., description="Ticket legible")):
    """
    Devuelve un turno por ticket. El service debe decodificar ticket -> rowid.
    """
    try:
        data: Optional[Dict[str, Any]] = _service.get_por_ticket(ticket)
        if not data:
            raise HTTPException(status_code=404, detail="no_encontrado")
        # Se espera que el service ya adjunte "ticket" y "id" si corresponde
        return data
    except ValueError as e:
        # p.ej., ticket mal formado
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/turnos/ticket/{ticket}", status_code=204)
async def delete_por_ticket(ticket: str = Path(..., description="Ticket legible")):
    """
    Elimina un turno por ticket. 204 si todo ok.
    """
    try:
        ok: bool = _service.delete_por_ticket(ticket)
        if not ok:
            # si el service devuelve False cuando no borró
            raise HTTPException(status_code=404, detail="no_encontrado")
        return  # 204
    except LookupError:
        raise HTTPException(status_code=404, detail="no_encontrado")
    except RuntimeError:
        # por ejemplo, regla de negocio: no cancelar a X horas del turno
        raise HTTPException(status_code=409, detail="no_permitido_por_regla")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/turnos/ticket/{ticket}")
async def patch_por_ticket(
    ticket: str = Path(..., description="Ticket legible"),
    cambios: TurnoPatchIn = ...,
):
    """
    Reprograma / edita campos del turno por ticket.
    """
    try:
        # Convertimos sólo campos presentes (excluimos None)
        payload = {k: v for k, v in cambios.model_dump().items() if v is not None}
        if not payload:
            raise HTTPException(status_code=400, detail="body_vacio_o_campos_invalidos")

        actualizado = _service.patch_por_ticket(ticket, payload)
        if not actualizado:
            raise HTTPException(status_code=404, detail="no_encontrado")
        return actualizado

    except LookupError:
        raise HTTPException(status_code=404, detail="no_encontrado")
    except RuntimeError:
        # choque de fecha/hora con otro turno
        raise HTTPException(status_code=409, detail="conflicto")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------ Mis turnos por contacto ------------

@app.get("/turnos/mios")
async def turnos_por_contacto(
    contacto: str = Query(..., description="Teléfono del cliente")
):
    """
    Lista turnos de un contacto (teléfono).
    Útil para que el bot muestre 'mis turnos' y el usuario elija uno por ticket.
    """
    try:
        items = _service.listar_por_contacto(contacto)
        # Se espera que el service adjunte "ticket" por cada item.
        return {"contacto": contacto, "turnos": items}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
#           Conexión bot Telegram (webhook)
# ============================================================

async def tg_send(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None),
):
    # 1. Seguridad (validar el token secreto)
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Webhook secret")

    # 2. Parsear el update que manda Telegram
    update = await request.json()
    message = update.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    # 3. Router de comandos
    if text.startswith("/start"):
        await tg_send(
            chat_id,
            "👋 ¡Hola! Soy tu bot de turnos.\n\n"
            "Comandos disponibles:\n"
            "• /disponibilidad YYYY-MM-DD\n"
            "• /reservar YYYY-MM-DD HH:MM servicio\n"
            "• /cancelar YYYY-MM-DD HH:MM\n",
        )

    elif text.startswith("/disponibilidad"):
        partes = text.split()
        if len(partes) < 2:
            await tg_send(
                chat_id,
                "Formato correcto:\n"
                "/disponibilidad 2025-11-20",
            )
        else:
            fecha = partes[1]
            servicio = partes[2] if len(partes) > 2 else None

            try:
                data = _service.get_disponibilidad(fecha=fecha, servicio=servicio)
                libres = data.get("libres", [])

                if not libres:
                    await tg_send(chat_id, f"❌ No hay turnos disponibles el {data['fecha']}.")
                else:
                    lista = "\n".join(f"• {h}" for h in libres)
                    await tg_send(
                        chat_id,
                        f"📅 Turnos disponibles el {data['fecha']}:\n\n{lista}",
                    )

            except ValueError as e:
                await tg_send(chat_id, f"⚠️ Error: {str(e)}")
            except Exception as e:
                await tg_send(chat_id, f"⚠️ Error inesperado: {type(e).__name__}: {e}")

    elif text.startswith("/reservar"):
        # /reservar 2025-11-20 10:00 Corte de pelo
        partes = text.split(maxsplit=3)
        if len(partes) < 4:
            await tg_send(
                chat_id,
                "Formato correcto:\n"
                "/reservar 2025-11-20 10:00 Corte de pelo",
            )
        else:
            fecha, hora, servicio = partes[1], partes[2], partes[3]
            try:
                data = {
                    "nombre_cliente": f"tg_{chat_id}",
                    "telefono_cliente": str(chat_id),
                    "fecha_turno": fecha,
                    "hora_turno": hora,
                    "servicio": servicio,
                }
                _service.reservar(data)
                await tg_send(
                    chat_id,
                    f"✅ Turno reservado:\n{fecha} {hora} - {servicio}",
                )
            except SlotOcupadoError:
                await tg_send(chat_id, "❌ Ese turno ya está ocupado.")
            except Exception as e:
                await tg_send(chat_id, f"⚠️ Error al reservar: {e}")

    elif text.startswith("/cancelar"):
        await tg_send(
            chat_id,
            "La función /cancelar todavía está en desarrollo. 🤓\n" 
            "Por ahora solo soportamos /disponibilidad y /reservar."
        )


    else:
        await tg_send(
            chat_id,
            "No entendí el comando.\n"
            "Usá /start para ver las opciones disponibles.",
        )

    return {"ok": True}
