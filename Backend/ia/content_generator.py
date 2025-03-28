from datetime import datetime

from langchain_core.output_parsers import JsonOutputParser
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain 
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate, MessagesPlaceholder

from models import RequirementResponse

class ContentGenerator:
    def __init__(
            self,
            document_manager,
            conversation_manager,
            llm: ChatGoogleGenerativeAI,
            thinking_manager

        ):
        self.document_manager = document_manager
        self.conversation_manager = conversation_manager
        self.thinking_manager= thinking_manager
        self.llm = llm
    
    def _manage_session(self, session_id, newchat):
        """Gestiona la creación o recuperación de una sesión"""
        if newchat or session_id is None:
            return self.conversation_manager.create_conversation(session_id)
        elif session_id not in self.conversation_manager.conversations:
            return self.conversation_manager.create_conversation(session_id)
        return session_id

    def _configure_retriever(self, session_id, newchat):
        """Configura el retriever adecuado según el tipo de conversación"""
        if newchat:
            return self.document_manager.vectorstore.as_retriever(
                search_type="similarity", 
                search_kwargs={"k": 5}
            )
        else:
            return self.conversation_manager.create_history_aware_retriever(session_id)

    def _prepare_prompt(self, query, preprompt, session_id, newchat):
        """Prepara el prompt con el formato adecuado para el LLM"""
        # Configurar instrucciones estructuradas
        parser = JsonOutputParser(pydantic_object=RequirementResponse)
        format_instructions = parser.get_format_instructions()
        
        # Crear mensaje del sistema
        system_message = self._create_system_message(preprompt, format_instructions)
        
        # Obtener historial formateado si existe y no es una nueva conversación
        history_messages = self.conversation_manager.format_chat_history(session_id) if not newchat else []
        
        if history_messages and not newchat:
            return ChatPromptTemplate.from_messages([
                ("system", system_message),
                *history_messages,
                ("human", f"Pregunta: {query}")
            ])
        else:
            return ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", f"Pregunta: {query}")
            ])

    
    def _create_system_message(self, preprompt, format_instructions):
        """Crea el mensaje del sistema con las instrucciones adecuadas"""
        escaped_format_instructions = format_instructions.replace('{', '{{').replace('}', '}}')
        return (
            f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta "
            "o como una base para construir lo que se te pide: \n\n{context}\n\n" 
            "Genera tu respuesta en el siguiente formato estructurado JSON. Asegúrate de incluir SIEMPRE el campo '{{status}}':\n\n"  # Escapamos {status}
            f"{escaped_format_instructions}\n\n"
            "IMPORTANTE: El campo '{{status}}' es OBLIGATORIO y debe ser uno de estos valores:\n"
            "- 'REQUERIMIENTOS_GENERADOS si puedes generar requerimientos en base a la descripcion del proyecto si es posible, no olvides que SIEMPRE debes usar los campos id (REQ-###) para funcionales y REQ-NF-### para no funcionales, title,description,category(funcional o no funcional segun el tipo de requerimiento) y priority (Alta, Media, Baja)'\n"
            "- 'INFORMACION_INSUFICIENTE cuando consideres que falta informacion, y listala dentro del campo missing_info'\n"
            "- 'ERROR_PROCESAMIENTO cuando surja un error'\n"
            "- 'RESPUESTA_GENERAL para una respuesta fuera de esos atributos '\n\n"
            "- Si te piden cualquier cosa que no sea un proyecto de software, responde textualmente:\n"
            "- 'Como asistente virtual no puedo proporcionarte la respuesta para eso, solo puedo asistirte con asistencia de proyectos de software'\n"
            "Finalmente, responde siempre en el lenguaje que te hablen."
        )

    async def _execute_rag_chain(self, query, retriever, qa_prompt):
        """Ejecuta la cadena RAG para obtener la respuesta"""
        # Crear la cadena de respuesta y recuperación
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        # Invocar la cadena para obtener la respuesta
        result = rag_chain.invoke({
            "input": query, 
            "\"description\"": "",
            "\"properties\"": "",
            "\"foo\"": ""
        })
    
        await self.thinking_manager.add_step("Analizando la información recuperada", 1.2)
        await self.thinking_manager.add_step("Sintetizando respuesta basada en el conocimiento disponible", 1.5)

        return result
    
    def _update_conversation_history(self, session_id, query, standardized_answer, response):
        """Actualiza el historial de conversación con la nueva interacción"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Actualizar el historial de la conversación
        self.conversation_manager.conversations[session_id]["history"].append({
            "query": query,
            "response": standardized_answer,
            "timestamp": timestamp,
            "raw_response": response.get('answer', 'No se encontró respuesta')
        })
            
        # Guardar el contexto recuperado para referencia
        if "context" in response:
            self.conversation_manager.conversations[session_id]["last_context"] = response["context"]
        
        self.conversation_manager.auto_save_history(session_id)
