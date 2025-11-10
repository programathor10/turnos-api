# En domain/interfaces.py
# Aquí definimos las interfaces de dominio para el sistema de turnos api 
# por ejemplo, interfaces para la gestión de turnos, pacientes, citas, etc.
# domain/interfaces.py
from abc import ABC, abstractmethod

class ITurnoRepository(ABC):
    @abstractmethod
    def get_turnos_ocupados(self, fecha: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def save_turno(self, turno_data: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def existe_turno(self, fecha: str, hora: str) -> bool:
        raise NotImplementedError
