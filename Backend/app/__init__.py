# Standard library imports

# Third-party imports
from fastapi import FastAPI 
from starlette.middleware.cors import CORSMiddleware

# Local application imports

from routes import epic_ai_router, req_ai_router, app_router,knowledge_ai_router   #<-- Futuras rutas de la API



def create_app() -> FastAPI:
    """
    Crea e inicializa una nueva instancia de la aplicación FastAPI.

    Returns:
        Una instancia de FastAPI configurada con todas las rutas y configuraciones necesarias.
    """
    print("Creando la aplicación FastAPI...")

    app = FastAPI(title="RAICES API", version="1.0.0")
    
    # Configuración del middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Permite todas las origenes despues sustituir con la URL de nuestro Front
        allow_credentials=True,
        allow_methods=["*"],  # Permite todos los métodos, especificar si es necesario -> ["GET", "POST", "PUT", "DELETE"]
        allow_headers=["*"],  # Permite todos los headers, especificar si fuere el caso -> ["X-Custom-Header"]
    )
    
    app.include_router(app_router)
    app.include_router(req_ai_router)
    app.include_router(epic_ai_router)
    app.include_router(knowledge_ai_router)
    # app.include_router(epic_router) 

    #app.include_router(name.router)<-- Cambiar name por el nombre de la ruta.py

    return app




