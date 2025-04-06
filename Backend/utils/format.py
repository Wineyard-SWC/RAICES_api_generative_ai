import json
from datetime import datetime
from typing import List, Dict


class Formats:

    def __init__(self):
        pass

    def merge_responses(self,f_response: str, nf_response: str) -> dict:
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
    

    def split_content(self,content: List[Dict], chunk_size: int = 5) -> List[List[Dict]]:
        """
        Divide el contenido en fragmentos más pequeños.
        Split content into smaller chunks to improve prompt performance.
        """
        return [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

    def fix_content_ids(self,content: List[Dict], type: str) -> List[Dict]:
        """
        Reasigna los IDs de las Historias de Usuario al formato US-### de forma secuencial.
        Reasigna los IDs de las Epicas al formato EPIC-### de forma secuencial.
        """

        fixed = []

        for i, gen_cont in enumerate(content, 1):
            new_cont = gen_cont.copy()
            if type == "epic": new_cont["id"] = f"EPIC-{i:03d}"
            else: new_cont["id"] = f"US-{i:03d}"
            fixed.append(new_cont)
        
        return fixed

    def format_requirements_for_prompt(self,requirements: List[Dict]) -> str:
        formatted = ""
        for req in requirements:
            formatted += f"- ({req.get('id')}) {req.get('title')}: {req.get('description')}\n"
        return formatted

    def format_epic_group_input(self,epic_group: list) -> str:
        prompt_input = ""
        for epic in epic_group:
            prompt_input += f"EPIC: {epic['title']} ({epic['id']})\nDescripción: {epic['description']}\nRequerimientos:\n"
            for req in epic.get("related_requirements", []):
                prompt_input += f"- {req['id']}: {req['description']}\n"
            prompt_input += "\n"
        return prompt_input
