# En repo/sheets_repo.py
# Aquí definimos el repositorio de Sheets para el sistema de turnos api 
# por ejemplo, repositorio para la gestión de turnos, pacientes, citas, etc.
from domain.interfaces import ITurnoRepository
from domain.models import Turno, Cliente, Servicio

class SheetsRepository(ITurnoRepository):
    pass