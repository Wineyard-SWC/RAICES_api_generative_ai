"""
Archivo: main.py
Descripción: Este módulo inicia la aplicación FastAPI, incluyendo la configuración del servidor.
Autores: Abdiel Fritsche Barajas
Fecha de Creación: 05-03-2025
"""
# Standard library imports
# Third-party imports
# Local application imports
from app import create_app     


print("Ejecutando la aplicación con Uvicorn...")
app = create_app() 



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)