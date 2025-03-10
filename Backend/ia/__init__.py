"""
Archivo: main.py
Descripción: Este modulo incluye la configuracion, inicializacion y metodos de la IA Generativa.
Autores: Abdiel Fritsche Barajas, Oscar Zhao Xu
Fecha de Creación: 05-03-2025
"""

# Standard library imports
import os
import uuid

#Third-party imports
#from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader,TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.chains.retrieval import create_retrieval_chain 
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# Local application imports


#load_dotenv(dotenv_path='../.env')
KEY = os.getenv("GEMINI_API_KEY")

class ProjectAssistantAI:
    """
    Gestiona documentos y la generación de contenido basado en AI para asistir en proyectos.

    Attributes:
        pdf_directory (str): Directorio donde se almacenan los documentos PDF.
        pdf_paths (list): Rutas a los archivos PDF cargados.
        persist_directory (str): Directorio para la persistencia de vectores.
        embedding_model (str): Modelo de embeddings utilizado para la generación de vectores.
        vectorstore (Chroma): Almacén de vectores para la recuperación de documentos.
        llm (ChatGoogleGenerativeAI): Modelo de lenguaje de Google para generación de respuestas.
        conversations (dict): Almacena el historial de conversaciones por ID de sesión.
    """

    def __init__(self, subdirectory, embedding_model = "models/embedding-001",persist_directory="/chroma_db"):
        """
        Inicializa el asistente del proyecto con la configuración de documentos y AI.

        Args:
            subdirectory (str): Subdirectorio dentro de 'pdfs' donde se almacenan los documentos.
            embedding_model (str): Modelo para generar embeddings, predeterminado a 'models/embedding-001'.
            persist_directory (str): Directorio base para almacenar vectores persistentes.
        """

        #Directorio de los pdfs
        self.pdf_directory = os.path.join(os.path.dirname(__file__), 'pdfs', subdirectory)
        #Path completo
        self.pdf_paths = [os.path.join(self.pdf_directory, f) for f in os.listdir(self.pdf_directory) if f.endswith('.pdf')]
        #Directorio permanente para cargar los documentos
        self.persist_directory = os.path.join(persist_directory, subdirectory)
        
        self.embedding_model = embedding_model
        self.vectorestore=None
        
        #Large Language Model Generative 
        self.llm = ChatGoogleGenerativeAI(
            api_key=KEY,
            model="gemini-1.5-pro",
            temperature=0.2,
            max_tokens=None,
            timeout=None
        )
        
        
        #Conversaciones
        self.conversations = {} 
        self.initialize_vectorstore()

    def initialize_vectorstore(self):
        """Inicializa o carga el almacén de vectores desde la persistencia"""
        # Crear embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            google_api_key=KEY,
            model=self.embedding_model
        )
        
        # Comprobar si existe un almacén persistente
        if os.path.exists(self.persist_directory) and len(os.listdir(self.persist_directory)) > 0:
            print(f"Cargando vectores existentes desde {self.persist_directory}")
            # Cargar vectores existentes
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings
            )
        else:
            print("Vectorizando documentos por primera vez...")
            # Asegúrate de que el directorio existe
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Cargar y vectorizar documentos
            documents = self.load_documents_from_directory(self.pdf_directory)
            
            # Crear nuevo almacén de vectores
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=self.persist_directory
            )
            # Guardar en disco
            print(f"Vectores guardados en {self.persist_directory}")
    
    def load_documents_from_directory(self, directory):
        """Carga documentos desde un directorio"""
        documents = []
        
        # Verificar si el directorio existe
        if not os.path.exists(directory):
            print(f"El directorio {directory} no existe.")
            return documents
        
        # Procesar archivos en el directorio
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            
            if os.path.isfile(filepath):
                # Manejar PDFs
                if filename.endswith('.pdf'):
                    loader = PyPDFLoader(filepath)
                    docs = loader.load()
                    documents.extend(docs)
                
                # Manejar TXTs
                elif filename.endswith('.txt'):
                    loader = TextLoader(filepath)
                    docs = loader.load()
                    documents.extend(docs)
        
        # Dividir documentos en chunks
        if documents:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            return text_splitter.split_documents(documents)
        
        return documents
    
    def add_document(self, content, metadata=None):
        """Añade un nuevo documento al almacén de vectores"""
        if metadata is None:
            metadata = {"source": "generated_content"}
        
        # Crear documento
        document = Document(page_content=content, metadata=metadata)
        
        # Dividir en chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents([document])
        
        # Añadir al almacén de vectores
        ids = self.vectorstore.add_documents(docs)
                
        return len(docs)
    
    def add_content_to_knowledge_base(self, content, source_name=None):
        """Añade contenido generado a la base de conocimientos"""
        if not source_name:
            source_name = f"generado_{len(os.listdir(self.pdf_directory)) + 1}.txt"
        
        # Guardar en archivo
        output_path = os.path.join(self.pdf_directory, source_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Añadir al vectorstore
        return self.add_document(content, metadata={"source": output_path})
    
    def create_conversation(self, session_id=None):
        """Crea o recupera una sesión de conversación con un ID único"""
        if session_id is None:
            session_id = str(uuid.uuid4())
            
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                "history": [],
                "last_context": None
            }
        return session_id
    
    def get_conversation_history(self, session_id):
        """Recupera el historial de conversación para un ID de sesión"""
        if session_id in self.conversations:
            return self.conversations[session_id]["history"]
        return []
    
    def format_chat_history(self, session_id):
        """Convierte el historial de conversación al formato necesario para LangChain"""
        history = self.get_conversation_history(session_id)
        formatted_history = []
        for entry in history:
            formatted_history.append(("human", entry["query"]))
            formatted_history.append(("ai", entry["response"]))
        return formatted_history
    
    def create_history_aware_retriever(self, session_id):
        """Crea un retriever que es consciente del contexto de la conversación"""
        base_retriever = self.vectorstore.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 5}
        )
        
        # Prompt para contextualizar la pregunta basada en el historial
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", "Dada la historia de chat y la última pregunta del usuario que podría hacer referencia al "
                      "contexto previo, formula una pregunta independiente que pueda entenderse sin el historial. "
                      "NO respondas la pregunta, solo reformúlala si es necesario o devuélvela tal como está."),
            *self.format_chat_history(session_id),
            ("human", "{input}")
        ])
        
        # Crear un retriever consciente del historial usando LangChain
        
        history_aware_retriever = create_history_aware_retriever(
            self.llm,
            base_retriever,
            contextualize_q_prompt
        )
        
        return history_aware_retriever
    
    async def generate_content(self, query, preprompt, session_id=None, newchat=False):
        """Genera contenido basado en la consulta y el historial de conversación"""
        # Si es una nueva conversación o no se proporciona session_id, creamos uno nuevo
        if newchat or session_id is None:
            session_id = self.create_conversation(session_id)
        elif session_id not in self.conversations:
            # Si el session_id no existe en el historial, lo creamos
            session_id = self.create_conversation(session_id)
        
        # Construir sistema de recuperación y generación de respuestas
        if newchat:
            # Para una nueva conversación, usamos el retriever básico
            retriever = self.vectorstore.as_retriever(
                search_type="similarity", 
                search_kwargs={"k": 5}
            )
        else:
            # Para conversaciones existentes, usamos el retriever consciente del historial
            retriever = self.create_history_aware_retriever(session_id)
        
        # Obtenemos el historial formateado para el prompt
        history_messages = self.format_chat_history(session_id)
        
        # Creamos el prompt para el sistema de respuestas
        system_message = (
            f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta "
            "o como una base para construir lo que se te pide:\n\n{context}"
        )
        
        # Construir el prompt completo con historial si existe
        if history_messages and not newchat:
            qa_prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                *history_messages,
                ("human", f"Pregunta: {query}")
            ])
        else:
            qa_prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", f"Pregunta: {query}")
            ])
        
        # Crear la cadena de respuesta y recuperación
        question_answer_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        # Invocar la cadena para obtener la respuesta
        response = rag_chain.invoke({"input": query})
        answer = response.get('answer', 'No se encontró respuesta')
        
        # Actualizar el historial de la conversación
        self.conversations[session_id]["history"].append({
            "query": query,
            "response": answer
        })
        
        # Guardar el contexto recuperado para referencia
        if "context" in response:
            self.conversations[session_id]["last_context"] = response["context"]
        
        return answer
