#Standard library imports
import asyncio 
import os
import uuid
from typing import Optional, List, Dict
import json
from datetime import datetime
# Third-party imports
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# Local application imports
from ia import Assistant
from models import RequestBody, ChatResponse, AddContentRequest, ChatMessage

router = APIRouter()

# Instancia de la IA con los documentos de requerimientos
RequirementsGenerativeAI = Assistant(
    subdirectory = 'requirements_pdfs',
)

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

def merge_responses(f_response: str, nf_response: str) -> dict:
        """
        Une dos respuestas del modelo (funcional y no funcional) en un solo JSON estandarizado.

        Merges two LLM responses (functional and non-functional) into a unified standardized JSON.
        """
        try:
            f_dict = json.loads(f_response)
        except json.JSONDecodeError:
            f_dict = {}

        try:
            nf_dict = json.loads(nf_response)
        except json.JSONDecodeError:
            nf_dict = {}

        f_items = f_dict.get("content", []) if isinstance(f_dict.get("content"), list) else []
        nf_items = nf_dict.get("content", []) if isinstance(nf_dict.get("content"), list) else []

        seen_ids = set()

        funcionales = []
        no_funcionales = []

        for item in f_items + nf_items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")

            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            if str(item_id).startswith("REQ-NF-"):
                item["category"] = "No Funcional"
                no_funcionales.append(item)
            
            else:
                item["category"] = "Funcional"
                funcionales.append(item)

        combined = {
            "status": "REQUERIMIENTOS_GENERADOS",
            "query": f_dict.get("query", "") or nf_dict.get("query", ""),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": {
                "funcionales": funcionales,
                "no_funcionales": no_funcionales
            },
            "missing_info": None,
            "metadata": None
        }

        return combined

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
        

        responsejson = merge_responses(f_response=functional_response,nf_response=non_functional_response)
        response_text = json.dumps(responsejson, indent=4, ensure_ascii=False)

        saved_to_kb = False
        
        if message.save_to_knowledge_base:
            kb_content = f"Pregunta: {message.message}\n\nRespuesta: {response_text}"
            chunks_added = RequirementsGenerativeAI.document_manager.add_content_to_knowledge_base(
                content=kb_content,
                source_name=f"chat_{session_id}_{uuid.uuid4()}.txt"
            )
            saved_to_kb = True
        
        return ChatResponse(
            message=response_text,
            session_id=session_id,
            saved_to_kb=saved_to_kb
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        history = RequirementsGenerativeAI.conversation_manager.get_conversation_history(session_id)
        return JSONResponse(content={"history": history}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
