# Standard library imports
import asyncio 
import os
from datetime import datetime
import json
from typing import List, Dict
# Third-party imports
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
# Local application imports
from ia import Assistant,shared_llm,shared_conversation_manager
from utils import Prompts, Formats, translate_selected_fields
from models import EpicRequestBody 


router = APIRouter()

EpicsGenerativeAI = Assistant(
    subdirectory='epics_pdfs',
    conversation_manager=shared_conversation_manager,
    llm=shared_llm
)

EpicsPrompt = Prompts()

JSONOutputFormater = Formats()

"""
Generar epicas 
"""
@router.post("/generate-epics")
async def generate_epics(body: EpicRequestBody):
    try:

        print(body.session_id)
        requirements_data = body.requirements_description

        all_requirements = requirements_data["funcionales"] + requirements_data["no_funcionales"]

        requirement_chunks = JSONOutputFormater.split_content(all_requirements, chunk_size=5)

        all_epics = []

        for chunk in requirement_chunks:
            prompt_input = JSONOutputFormater.format_requirements_for_prompt(chunk)

            partial_epics = await EpicsGenerativeAI.generate_content(
                query=prompt_input,
                preprompt=EpicsPrompt.getEPICprompt(),
                session_id=body.session_id,
                type="epicas",
                newchat=False
            )

            parsed = json.loads(partial_epics)
            if isinstance(parsed.get("content"), list):
                all_epics.extend(parsed["content"])

        response = JSONOutputFormater.fix_content_ids(all_epics,"epic")

        final_response = {
            "status": "EPICAS_GENERADOS",
            "query": requirement_chunks,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": response,
            "missing_info": None,
            "metadata": None
        }

        lang = body.lang
        if lang:
            final_response = translate_selected_fields(final_response, target_lang=lang)

        final_response_text = json.dumps(final_response, indent=4, ensure_ascii=False)
        
        EpicsGenerativeAI.conversation_manager.load_conversation_histories()
            

        EpicsGenerativeAI.conversation_manager.conversations[body.session_id]["history"].append(
            {
                "query": str(requirement_chunks),
                "response":final_response_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "raw_response": final_response
            }
        )

        EpicsGenerativeAI.conversation_manager.auto_save_history(body.session_id)

        return JSONResponse(content=final_response, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
