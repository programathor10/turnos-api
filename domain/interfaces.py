# En domain/interfaces.py
# Aquí definimos las interfaces de dominio para el sistema de turnos api 
# por ejemplo, interfaces para la gestión de turnos, pacientes, citas, etc.
from abc import ABC, abstractmethod
from domain.models import Turno, Cliente, Servicio

class ITurnoRepository(ABC):
    pass