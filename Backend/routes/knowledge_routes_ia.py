from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse


from ia import Assistant
from models import AddContentRequest

router = APIRouter()


GenerativeAI = Assistant(
    subdirectory = ''
)
    
@router.post("/knowledge/add")
async def add_to_knowledge_base(request: AddContentRequest):
    try:
        chunks_added = GenerativeAI.document_manager.add_content_to_knowledge_base(
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
        history = GenerativeAI.conversation_manager.get_conversation_history(session_id)
        
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
        
        chunks_added = GenerativeAI.document_manager.add_content_to_knowledge_base(
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