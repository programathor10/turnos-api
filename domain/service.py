# # En domain/service.py
# # Aquí definimos los servicios de dominio para el sistema de turnos api 
# # por ejemplo, servicios para la gestión de turnos, pacientes, citas, etc.
# domain/service.py
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from domain.models import Turno
from domain.interfaces import ITurnoRepository

TZ = ZoneInfo("America/Argentina/Buenos_Aires")

class SlotOcupadoError(Exception):
    pass

class TurnoService:
    # Config fija para Pasada 2 (en Pasada 4 saldrá de Sheets)
    OPEN_TIME = "09:00"
    CLOSE_TIME = "18:00"
    SLOT_MIN = 30
    SERVICIOS = {"corte", "color"}

    def __init__(self, turno_repository: ITurnoRepository):
        self.repo = turno_repository

    # ---------- Helpers ----------
    def _parse_hhmm(self, hhmm: str) -> time:
        try:
            return datetime.strptime(hhmm, "%H:%M").time()
        except Exception:
            raise ValueError("hora_invalida")

    def _is_multiple(self, t: time, start: time, step_min: int) -> bool:
        m = t.hour * 60 + t.minute
        s = start.hour * 60 + start.minute
        return (m - s) % step_min == 0

    def _gen_malla(self, fecha: str) -> list[str]:
        ini = self._parse_hhmm(self.OPEN_TIME)
        fin = self._parse_hhmm(self.CLOSE_TIME)
        step = timedelta(minutes=self.SLOT_MIN)

        cur = datetime.combine(datetime.strptime(fecha, "%Y-%m-%d").date(), ini)
        end = datetime.combine(datetime.strptime(fecha, "%Y-%m-%d").date(), fin)

        slots: list[str] = []
        while cur <= end:
            slots.append(cur.strftime("%H:%M"))
            cur += step
        return slots

    # ---------- Público ----------
    def get_disponibilidad(self, fecha: str, servicio: str | None = None) -> dict:
        # servicio opcional (en Pasada 2 no afecta malla)
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except Exception:
            raise ValueError("fecha_invalida")

        malla = self._gen_malla(fecha)
        ocupados = set(self.repo.get_turnos_ocupados(fecha))
        libres = [h for h in malla if h not in ocupados]

        # Si es hoy, quitar horas pasadas
        hoy_bsas = datetime.now(TZ).date()
        if datetime.strptime(fecha, "%Y-%m-%d").date() == hoy_bsas:
            ahora_hhmm = datetime.now(TZ).strftime("%H:%M")
            libres = [h for h in libres if h >= ahora_hhmm]

        return {"fecha": fecha, "libres": libres}

    def reservar(self, data: dict) -> Turno:
        # Validaciones básicas
        if data.get("servicio", "").strip().lower() not in self.SERVICIOS:
            raise ValueError("servicio_invalido")

        try:
            fecha = datetime.strptime(data["fecha_turno"], "%Y-%m-%d").date()
        except Exception:
            raise ValueError("fecha_invalida")

        try:
            hora = self._parse_hhmm(data["hora_turno"])
        except ValueError:
            raise ValueError("hora_invalida")

        # Malla y pertenencia
        open_t = self._parse_hhmm(self.OPEN_TIME)
        close_t = self._parse_hhmm(self.CLOSE_TIME)
        if not (open_t <= hora <= close_t):
            raise ValueError("hora_fuera_de_rango")
        if not self._is_multiple(hora, open_t, self.SLOT_MIN):
            raise ValueError("hora_no_cae_en_slot")

        # Duplicado
        fecha_s = fecha.strftime("%Y-%m-%d")
        hora_s = f"{hora.hour:02d}:{hora.minute:02d}"
        if self.repo.existe_turno(fecha_s, hora_s):
            raise SlotOcupadoError("ocupado")

        # Guardar
        turno = Turno(**{
            "nombre_cliente": data["nombre_cliente"],
            "telefono_cliente": data["telefono_cliente"],
            "fecha_turno": fecha_s,
            "hora_turno": hora_s,
            "servicio": data["servicio"].strip().lower(),
            "estado": "reservado",
        })
        self.repo.save_turno(turno.model_dump())
        return turno



# from domain.interfaces import ITurnoRepository
# from domain.models import Turno, Cliente, Servicio
# from datetime import datetime
# from config_service.settings import Hora_inicio, Hora_fin, Duracion_turno
# from zoneinfo import ZoneInfo



# class TurnoService:
#     def __init__(self, turno_repository: ITurnoRepository):
#         pass
#     # 2. Dentro del método generador de malla (conceptual):
#     def generar_malla(self):
#         inicio = Hora_inicio
#         fin = Hora_fin
#         duracion = Duracion_turno

#         # Lógica de bucle para crear la lista de 9:00, 9:30, 10:00
#         turnos = []
#         while inicio < fin:
#             turnos.append(inicio)
#             inicio += duracion
#         return turnos


#     def get_disponibilidad(self, fecha: datetime):
#         turnos = self.generar_malla()
#         turnos_ocupados = self.turno_repository.get_turnos_ocupados(fecha)
#         turnos_disponibles = [
#             turno for turno in turnos if turno not in turnos_ocupados
#         ]

#         # --- LÓGICA FALTANTE ---

#         # 1. Obtener la hora actual en la TZ de la aplicación
#         # Se recomienda que tu objeto 'fecha' de entrada sea un objeto date, no datetime.
#         TZ_ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")
#         ahora_tz = datetime.now(TZ_ARGENTINA)

#         # 2. Comparar la fecha solicitada con la fecha de hoy
#         if fecha.date() == ahora_tz.date():
#             # Si la fecha solicitada ES HOY, filtramos los slots pasados.
            
#             horarios_futuros = []
#             for hora_slot in turnos_disponibles:
#                 # Convertir el string "HH:MM" a un objeto datetime localizable (en Argentina)
                
#                 # Construimos un objeto datetime con la fecha del turno y la hora del slot
#                 hora_completa_slot = datetime.combine(
#                     fecha.date(), 
#                     datetime.strptime(hora_slot, "%H:%M").time(),
#                     tzinfo=TZ_ARGENTINA # Le asignamos la TZ local
#                 )
                
#                 # Comparamos el slot con la hora actual
#                 if hora_completa_slot > ahora_tz:
#                     horarios_futuros.append(hora_slot)
            
#             return horarios_futuros # Retornamos solo los que no han pasado

#         # Si la fecha solicitada NO ES HOY (es mañana o en el futuro), retornamos todo
#         return turnos_disponibles
        
#         pass
