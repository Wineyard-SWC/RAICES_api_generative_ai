#Standard library imports
import asyncio 
import os
import uuid

# Third-party imports
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict

# Local application imports
from ia import ProjectAssistantAI as Assistant
from models import RequestBody, ChatResponse, AddContentRequest, ChatMessage
router = APIRouter()

# Instancia de la IA con los documentos de requerimientos
RequirementsGenerativeAI = Assistant(subdirectory='requirements_pdfs', persist_directory="./chroma_db")

# PROMPTS BASE EXISTENTES
FunctionalRequirementsPrompt = (
    "Imagina que eres un SCRUM Master con 20 años de experiencia en metodologías Agile. "
    "Tu tarea es generar requisitos funcionales detallados y específicos basados en "
    "la descripción del proyecto que se te proporcionará. Debes ser conciso y evitar redundancias. "
    "Responde únicamente cuando recibas una descripción clara y válida de un proyecto de software. "
    "Si la descripción del proyecto es insuficiente para generar los requerimientos, pide detalles "
    "específicos que falten. Por ejemplo, si necesitas más información sobre los usuarios finales "
    "del sistema o los objetivos específicos del proyecto, indícalo claramente. Presenta los requerimientos "
    "en una lista clara. Basate en el siguiente ejemplo: "
    "1. Inicio de sesión de usuario: El sistema debe permitir a los usuarios iniciar sesión utilizando un nombre de usuario y contraseña válidos. "
    "2. Procesamiento de Negocios: El sistema debe procesar los pagos con tarjeta de crédito y proporcionar a los usuarios un recibo cuando las transacciones sean exitosas."
)

NonFunctionalRequirementsPrompt = (
    "Imagina que eres un SCRUM Master con 20 años de experiencia en metodologías Agile. "
    "Tu tarea es generar requisitos no funcionales detallados y específicos basados en "
    "la descripción del proyecto que se te proporcionará. Debes ser conciso y evitar redundancias. "
    "Responde únicamente cuando recibas una descripción clara y válida de un proyecto de software. "
    "Si la descripción del proyecto es insuficiente para generar los requerimientos, pide detalles "
    "específicos que falten. Por ejemplo, si necesitas más información sobre los usuarios finales "
    "del sistema o los objetivos específicos del proyecto, indícalo claramente. Presenta los requerimientos "
    "en una lista clara. Basate en el siguiente ejemplo: "
    "Velocidad de rendimiento: El sistema debe procesar las solicitudes de los usuarios en un plazo promedio de 2 segundos, incluso con mucho tráfico de usuarios. "
    "Disponibilidad del sistema: El sistema debe mantener un tiempo de actividad del 99.9 % para garantizar que los usuarios tengan acceso constante."
)

# Generar requerimientos funcionales
async def generate_functional_requirements(project_description, session_id=None):
    return await RequirementsGenerativeAI.generate_content(
        query=project_description,
        preprompt=FunctionalRequirementsPrompt,
        session_id=session_id
    )
    
# Generar requerimientos no funcionales
async def generate_non_functional_requirements(project_description, session_id=None):
    return await RequirementsGenerativeAI.generate_content(
        query=project_description,
        preprompt=NonFunctionalRequirementsPrompt,
        session_id=session_id
    )

@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    # Si no se envía session_id o se quiere forzar una nueva conversación, generamos uno nuevo.
    if not message.session_id:
        session_id = str(uuid.uuid4())
        new_conversation = True
    else:
        session_id = message.session_id
        new_conversation = False  

    try:
        # Llamamos a cada función de requerimientos pasando el flag newchat según corresponda.
        functional_response = await RequirementsGenerativeAI.generate_content(
            query=message.message,
            preprompt=FunctionalRequirementsPrompt,
            session_id=session_id,
            newchat=new_conversation
        )
        non_functional_response = await RequirementsGenerativeAI.generate_content(
            query=message.message,
            preprompt=NonFunctionalRequirementsPrompt,
            session_id=session_id,
            newchat=new_conversation
        )
        
        response_text = functional_response + " " + non_functional_response
        saved_to_kb = False
        
        if message.save_to_knowledge_base:
            kb_content = f"Pregunta: {message.message}\n\nRespuesta: {response_text}"
            chunks_added = RequirementsGenerativeAI.add_content_to_knowledge_base(
                content=kb_content,
                source_name=f"chat_{session_id}_{uuid.uuid4()}.txt"
            )
            saved_to_kb = True
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            saved_to_kb=saved_to_kb
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        history = RequirementsGenerativeAI.get_conversation_history(session_id)
        return JSONResponse(content={"history": history}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/knowledge/add")
async def add_to_knowledge_base(request: AddContentRequest):
    try:
        chunks_added = RequirementsGenerativeAI.add_content_to_knowledge_base(
            content=request.content,
            source_name=request.source_name
        )
        
        return JSONResponse(content={
            "message": f"Contenido añadido a la base de conocimientos. Se crearon {chunks_added} fragmentos.",
            "chunks_added": chunks_added
        }, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/learn-from-response")
async def learn_from_response(
    session_id: str, 
    response_index: int = -1,  
    save_as: Optional[str] = None
):
    try:
        history = RequirementsGenerativeAI.get_conversation_history(session_id)
        
        if not history:
            raise HTTPException(status_code=404, detail="No hay historial para esta sesión")
        
        if response_index < 0:
            response_index = len(history) + response_index
        
        if response_index < 0 or response_index >= len(history):
            raise HTTPException(status_code=400, detail="Índice de respuesta fuera de rango")
        
        entry = history[response_index]
        content = f"Pregunta: {entry['query']}\n\nRespuesta: {entry['response']}"
        
        if not save_as:
            save_as = f"learned_{session_id}_{response_index}.txt"
        
        chunks_added = RequirementsGenerativeAI.add_content_to_knowledge_base(
            content=content,
            source_name=save_as
        )
        
        return JSONResponse(content={
            "message": f"Respuesta añadida a la base de conocimientos. Se crearon {chunks_added} fragmentos.",
            "content": content,
            "file": save_as
        }, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
