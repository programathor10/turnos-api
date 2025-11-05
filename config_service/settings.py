# En config_service/settings.py (o donde manejes las variables de entorno)
import os

# Se lee del archivo .env o .env.example
# Usaremos pytz o zoneinfo (Python 3.9+) para manejar la TZ
APP_TIMEZONE = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")