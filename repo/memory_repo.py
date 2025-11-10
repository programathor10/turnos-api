# repo/memory_repo.py
from domain.interfaces import ITurnoRepository

class MemoryTurnoRepository(ITurnoRepository):
    def __init__(self) -> None:
        # "libreta" en memoria
        self.turnos: dict[str, dict] = {}

    def _key(self, fecha: str, hora: str, servicio: str) -> str:
        return f"{fecha}|{hora}|{servicio}"

    def get_turnos_ocupados(self, fecha: str) -> list[str]:
        prefijo = f"{fecha}|"
        horas = []
        for k in self.turnos.keys():
            if k.startswith(prefijo):
                _, hora, _ = k.split("|", 2)
                horas.append(hora)
        # sin duplicados + ordenado
        return sorted(set(horas))

    def existe_turno(self, fecha: str, hora: str) -> bool:
        # Política simple Pasada 2: 1 solo turno por fecha+hora (sin importar servicio)
        prefijo = f"{fecha}|{hora}|"
        return any(k.startswith(prefijo) for k in self.turnos.keys())

    def save_turno(self, turno_data: dict) -> None:
        fecha = turno_data["fecha_turno"]
        hora = turno_data["hora_turno"]
        servicio = turno_data["servicio"].strip().lower()
        key = self._key(fecha, hora, servicio)
        if key in self.turnos:
            raise KeyError("duplicado")
        self.turnos[key] = turno_data
