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
from ia import Assistant
from utils import Prompts, Formats
from models import EpicRequestBody 

router = APIRouter()

EpicsGenerativeAI = Assistant(
    subdirectory='epics_pdfs'
)

EpicsPrompt = Prompts()

JSONOutputFormater = Formats()

"""
Generar epicas 
"""
@router.post("/generate-epics")
async def generate_epics(body: EpicRequestBody):
    try:
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

        final_response = {
            "status": "EPICAS_GENERADOS",
            "query": requirement_chunks,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": JSONOutputFormater.fix_content_ids(all_epics,"epic"),
            "missing_info": None,
            "metadata": None
        }

        return JSONResponse(content=final_response, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
