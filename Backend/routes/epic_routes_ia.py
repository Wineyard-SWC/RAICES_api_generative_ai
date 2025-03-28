# Standard library imports
import asyncio 
import os
# Third-party imports
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
# Local application imports
from ia import Assistant


router = APIRouter()

EpicsGenerativeAI = Assistant(
    subdirectory='epics_pdfs'
)

#PROMPTS BASE
EpicsPrompt = "Imagina que eres un Product Owner con amplia experiencia en metodologías Agile, " \
"especialmente en Scrum. Tu tarea es formular épicas claras y comprensivas que resuman grandes" \
" áreas de funcionalidad basadas en los requerimientos que te daran del proyecto. Estos" \
" requerimientos abarcan las necesidades estratégicas y funcionales del negocio, y tu objetivo" \
" es asegurar que las épicas reflejen estos objetivos de alto nivel de una manera que guíe " \
" efectivamente el desarrollo del proyecto. Debes ser conciso y evitar detalles técnicos profundos," \
" ya que las épicas deben ser lo suficientemente amplias para abarcar varias historias de usuario" \
" pero específicas para dirigir el desarrollo. Las épicas deben presentarse en una lista clara," \
" proporcionando un marco que pueda desglosarse en historias de usuario más detalladas durante" \
" las fases de sprint. Por ejemplo, puedes considerar las siguientes épicas basadas en los tipos" \
" de requerimientos típicos:" \
"1. **Automatización de la Interacción con el Cliente**: Desarrollar un sistema que automatice las interacciones entre los clientes y la plataforma, desde el soporte inicial hasta las consultas de seguimiento, mejorando la eficiencia y la satisfacción del cliente." \
"2. **Expansión de la Plataforma Móvil**: Crear funcionalidades robustas para la aplicación móvil que permitan una gestión completa y segura del usuario, mejorando la accesibilidad y el engagement en dispositivos móviles."


class RequestBody(BaseModel):
    requirements_description: str

"""
Generar epicas 
"""
@router.post("/generate-epics")
async def generate_requirements(body: RequestBody):
    requirements_description = body.requirements_description
    try: 
        epics_response = await EpicsGenerativeAI.generate_content(
            query=requirements_description,
            preprompt=EpicsPrompt
        )
        return JSONResponse(content={
            "Epics": epics_response,
        }, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))