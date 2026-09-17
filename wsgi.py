import sys
import os

# Asegurar que el directorio de la aplicación esté en el path de Python
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

# Importar la instancia de la aplicación Flask
from app import app as application
