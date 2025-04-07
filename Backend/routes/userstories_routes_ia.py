from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List
import json
from ia import Assistant
from utils import Prompts, Formats
from models import StoryRequestBody

# Instancia del asistente para historias de usuario
UserStoriesAI = Assistant(subdirectory='stories_pdfs')

UserStoryPrompt = Prompts()
USprompt = UserStoryPrompt.getUSprompt()

router = APIRouter()


JSONOutputFormater = Formats()

@router.post("/generate-user-stories")
async def generate_user_stories(body: StoryRequestBody):
    try:
        epics_data = body.epic_description

        epics = epics_data["content"]

        epic_groups = JSONOutputFormater.split_content(epics)
        all_user_stories = []

        for group in epic_groups:
            input_text = JSONOutputFormater.format_epic_group_input(group)

            partial_user_stories = await UserStoriesAI.generate_content(
                query=input_text,
                preprompt=UserStoryPrompt,
                session_id=body.session_id,
                type="historias_usuario",
                newchat=False
            )

            parsed = json.loads(partial_user_stories)
            if isinstance(parsed.get("content"), list):
                all_user_stories.extend(parsed["content"])

        response = JSONOutputFormater.fix_content_ids(all_user_stories,"US")

        final_response = {
            "status": "HISTORIAS_GENERADAS",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": response,
            "missing_info": None,
            "metadata": None
        }

        final_response_text = json.dumps(final_response, indent=4, ensure_ascii=False)
        
        UserStoriesAI.conversation_manager.conversations[body.session_id]["history"].append(
            {
                "query": str(epics_data),
                "response":final_response_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "raw_response": final_response
            }
        )

        UserStoriesAI.conversation_manager.auto_save_history(body.session_id)


        return JSONResponse(content=final_response, status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
