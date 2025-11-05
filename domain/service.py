# En domain/service.py
# Aquí definimos los servicios de dominio para el sistema de turnos api 
# por ejemplo, servicios para la gestión de turnos, pacientes, citas, etc.
from domain.interfaces import ITurnoRepository
from domain.models import Turno, Cliente, Servicio
from datetime import datetime
from config_service.settings import Hora_inicio, Hora_fin, Duracion_turno
from zoneinfo import ZoneInfo



class TurnoService:
    def __init__(self, turno_repository: ITurnoRepository):
        pass
    # 2. Dentro del método generador de malla (conceptual):
    def generar_malla(self):
        inicio = Hora_inicio
        fin = Hora_fin
        duracion = Duracion_turno

        # Lógica de bucle para crear la lista de 9:00, 9:30, 10:00
        turnos = []
        while inicio < fin:
            turnos.append(inicio)
            inicio += duracion
        return turnos


    def get_disponibilidad(self, fecha: datetime):
        turnos = self.generar_malla()
        turnos_ocupados = self.turno_repository.get_turnos_ocupados(fecha)
        turnos_disponibles = [
            turno for turno in turnos if turno not in turnos_ocupados
        ]

        # --- LÓGICA FALTANTE ---

        # 1. Obtener la hora actual en la TZ de la aplicación
        # Se recomienda que tu objeto 'fecha' de entrada sea un objeto date, no datetime.
        TZ_ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")
        ahora_tz = datetime.now(TZ_ARGENTINA)

        # 2. Comparar la fecha solicitada con la fecha de hoy
        if fecha.date() == ahora_tz.date():
            # Si la fecha solicitada ES HOY, filtramos los slots pasados.
            
            horarios_futuros = []
            for hora_slot in turnos_disponibles:
                # Convertir el string "HH:MM" a un objeto datetime localizable (en Argentina)
                
                # Construimos un objeto datetime con la fecha del turno y la hora del slot
                hora_completa_slot = datetime.combine(
                    fecha.date(), 
                    datetime.strptime(hora_slot, "%H:%M").time(),
                    tzinfo=TZ_ARGENTINA # Le asignamos la TZ local
                )
                
                # Comparamos el slot con la hora actual
                if hora_completa_slot > ahora_tz:
                    horarios_futuros.append(hora_slot)
            
            return horarios_futuros # Retornamos solo los que no han pasado

        # Si la fecha solicitada NO ES HOY (es mañana o en el futuro), retornamos todo
        return turnos_disponibles
        
        pass
