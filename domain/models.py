# En domain/models.py
# Aquí definimos los modelos de dominio
from pydantic import BaseModel

class Turno(BaseModel):
    nombre_cliente: str
    telefono_cliente: str
    fecha_turno: str
    hora_turno: str
    pass

class Cliente(BaseModel):
    pass

class Servicio(BaseModel):
    pass

class disponibilidad(BaseModel):
    fecha: str
    turnos: list[str]