import os

from langchain_google_genai import ChatGoogleGenerativeAI

from .document_manager import DocumentManager
from .conversation_manager import ConversationManager
from .llm_response_manager import LLMResponseProcessor
from .content_generator import ContentGenerator
from .thinking_steps import ThinkingSteps


Key = os.getenv("GEMINI_API_KEY")
Embedding = os.getenv("EMBEDDING")



class Assistant:
    def __init__(
            self, 
            subdirectory:str,
            embedding_model:str = Embedding, 
            persist_directory:str = os.path.join(os.path.dirname(__file__), "/chroma_db"),
            filter_directories:str = None,
            thinking_callback:str = None
        ):
        self.llm = ChatGoogleGenerativeAI(
            api_key=Key,
            model="gemini-2.0-flash",
            temperature=0.2,
            max_tokens=None,
            timeout=None,
        )

        self.llm_response_manager = LLMResponseProcessor(
            llm= self.llm
        )
        
        self.document_manager = DocumentManager(
            KEY= Key,
            pdf_directory= os.path.join(os.path.dirname(__file__), 'pdfs', subdirectory),
            persist_directory=persist_directory,
            embedding= embedding_model,
            filter_directories=filter_directories
        )

        self.conversation_manager = ConversationManager(
            document_manager= self.document_manager,
            llm = self.llm
        )

        self.thinking_manager = ThinkingSteps(
            callback=thinking_callback
        )

        self.content_generator = ContentGenerator(
            conversation_manager= self.conversation_manager,
            document_manager= self.document_manager,
            llm= self.llm,
            thinking_manager= self.thinking_manager
        )


    async def generate_content(self, query, preprompt, session_id=None, newchat=False):
        """Genera contenido basado en la consulta y el historial de conversación"""
        # Gestionar la sesión
        session_id = self.content_generator._manage_session(session_id, newchat)
        
        # Configurar el retriever adecuado según el tipo de conversación
        retriever = self.content_generator._configure_retriever(session_id, newchat)
        
        # Preparar el prompt con el formato adecuado
        await self.thinking_manager.add_step("Analizando la consulta...", 1.5)
        qa_prompt = self.content_generator._prepare_prompt(query, preprompt, session_id, newchat)
        
        await self.thinking_manager.add_step("Buscando información relevante en la base de conocimiento", 2.0)
        await self.thinking_manager.add_step("Procesando documentos recuperados y generando respuesta", 2.5)
        # Crear y ejecutar la cadena RAG
        response = await self.content_generator._execute_rag_chain(query, retriever, qa_prompt)
        
        # Procesar la respuesta
        standardized_answer = self.llm_response_manager.process_llm_response(response,query)
        
        # Actualizar el historial
        self.content_generator._update_conversation_history(session_id, query, standardized_answer, response)
        
        await self.thinking_manager.complete()

        return standardized_answer
