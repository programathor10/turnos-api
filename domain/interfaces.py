# En domain/interfaces.py
# Aquí definimos las interfaces de dominio para el sistema de turnos api 
# por ejemplo, interfaces para la gestión de turnos, pacientes, citas, etc.
from abc import ABC, abstractmethod
from domain.models import Turno, Cliente, Servicio
from datetime import datetime

class ITurnoRepository(ABC):
    @abstractmethod
    def get_turnos_ocupados(self, fecha: datetime):
        raise NotImplementedError
    pass