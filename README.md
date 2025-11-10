# 🧾 Turnos API  
**Sistema de gestión de turnos** desarrollado con **Python, FastAPI y SQLite3**.  
Permite consultar disponibilidad, reservar turnos y mantener persistencia en una base de datos local.

---

## 🚀 Tecnologías utilizadas
- **Python 3.11**
- **FastAPI**
- **SQLite3**
- **Pydantic**
- **Uvicorn**

---

## 🧠 Descripción del proyecto
Esta API fue desarrollada como práctica personal para entender la estructura de una aplicación backend real.  
El sistema permite manejar turnos de forma sencilla, validando duplicados y guardando la información en una base de datos persistente (SQLite).  

La arquitectura está basada en **capas separadas**:
- `main.py` → Define los endpoints y configura la app.  
- `service.py` → Contiene la lógica del negocio (validaciones y flujo).  
- `repo/sqlite_repo.py` → Se encarga de la comunicación con la base de datos.  
- `domain/interfaces.py` → Define las interfaces que deben cumplir los repositorios.

---

## ⚙️ Instalación y uso

### 1️⃣ Clonar el repositorio
```bash
git clone https://github.com/programathor10/turnos-api.git
cd turnos-api
