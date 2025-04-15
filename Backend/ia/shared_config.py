import os
import dotenv

from .conversation_manager import ConversationManager
from langchain_google_genai import ChatGoogleGenerativeAI


dotenv.load_dotenv()
Key = os.environ.get("GEMINI_API_KEY")


# Configura un LLM compartido
shared_llm = ChatGoogleGenerativeAI(
    api_key=Key,
    model="gemini-2.0-flash",
    temperature=0.2,
    max_tokens=None,
    timeout=None,
)

# Crea un conversation_manager independiente (sin document_manager)
# Modifica tu ConversationManager para que acepte el document_manager después
class SharedConversationManager(ConversationManager):
    def __init__(self, llm):
        self.llm = llm
        self.document_manager = None
        self.conversations = {}
        self.load_conversation_histories()
        
    def set_document_manager(self, document_manager):
        """Actualiza el document_manager según el contexto"""
        self.document_manager = document_manager

shared_conversation_manager = SharedConversationManager(llm=shared_llm)