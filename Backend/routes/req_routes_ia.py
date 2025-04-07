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
from utils import Prompts, Formats
router = APIRouter()

# Instancia de la IA con los documentos de requerimientos
RequirementsGenerativeAI = Assistant(
    subdirectory = 'requirements_pdfs',
)

RequirementsPrompt = Prompts()
Fprompt,NFprompt = RequirementsPrompt.getREQprompt()

JSONOutputFormater = Formats()





@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):

    if not message.session_id:
        session_id = str(uuid.uuid4())
        new_conversation = True
    else:
        session_id = message.session_id
        new_conversation = False  

    try:
        functional_response = await RequirementsGenerativeAI.generate_content(
            query=message.message,
            preprompt=Fprompt,
            session_id=session_id,
            newchat=new_conversation,
            type="requerimientos"
        )

        non_functional_response = await RequirementsGenerativeAI.generate_content(
            query=message.message,
            preprompt=NFprompt,
            session_id=session_id,
            newchat=new_conversation,
            type="requerimientos"
        )

        responsejson = JSONOutputFormater.merge_responses(f_response=functional_response,
                                                          nf_response=non_functional_response
                                                            )
                                
        response_text = json.dumps(responsejson["content"],
                                    indent=4,
                                    ensure_ascii=False
                                    )

        RequirementsGenerativeAI.conversation_manager.conversations[session_id]["history"].append(
            {
                "query":message.message,
                "response":response_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "raw_response": responsejson
            }
        )

        RequirementsGenerativeAI.conversation_manager.auto_save_history(session_id)

        
        return ChatResponse(
            message=responsejson,
            session_id=session_id,
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
    
