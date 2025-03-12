"""
Archivo: main.py
Descripción: Este modulo incluye la configuracion, inicializacion y metodos de la IA Generativa.
Autores: Abdiel Fritsche Barajas, Oscar Zhao Xu
Fecha de Creación: 05-03-2025
"""

# Standard library imports
import os
import uuid
import re
import json
#Third-party imports
#from dotenv import load_dotenv
from datetime import datetime
from langchain_community.document_loaders import PyPDFLoader,TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.chains.retrieval import create_retrieval_chain 
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser
from models import RequirementResponse
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

    def __init__(self, subdirectory, embedding_model = "models/embedding-001",persist_directory= os.path.join(os.path.dirname(__file__), "/chroma_db")):
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

        #Cargar almacen de vectores
        self.initialize_vectorstore()

        #Cargar historiales de conversacion existentes
        self.load_conversation_histories()

    """
    FUNCIONES PARA AGREGAR Y CARGAR CONTENIDO AL RAG (GENERACION AUMENTADA POR RECUPERACION)
    """

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
    
    
    """
    FUNCIONES PARA CREACION, MANIPULACION, ACCESO Y EDICION DEL HISTORIAL DE CONVERSACIONES CON LA IA
    """
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
    
    def save_conversation_history(self,session_id):
        """
        Guarda el historial de una conversacion especifica en un archivo txt
        Args:
            session_id(str): ID de la sesion cuyo historial se desea
        Returns:
            bool: True si se guardo correctamente, False en caso contrario
        """

        # Crear directorio para historiales si no existe
        if session_id not in self.conversations:
            print(f"No existe historial para la sesion {session_id}")
            return False
        
        history_dir = os.path.join(os.path.dirname(__file__),'conversation_histories')
        os.makedirs(history_dir, exist_ok=True)

        history_file = os.path.join(history_dir,f"{session_id}.txt")

        try:
            with open(history_file,'a',encoding='utf-8') as f:
                current_history = self.conversations[session_id]["history"]

                saved_count = 0
                
                if os.path.exists(history_file):
                    with open(history_file,'r',encoding='utf-8') as read_file:
                        saved_count = read_file.read().count("--- Fin de respuesta ---")
                
                for i in range(saved_count, len(current_history)):
                    entry = current_history[i]
                    timestamp = entry.get("timestamp","N/A")
                    query = entry["query"]
                    response = entry["response"]

                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Pregunta: {query}\n\n")
                    f.write(f"Respuesta: {response}\n")
                    f.write(f"--- Fin de respuesta ---\n\n")
            return True
        except Exception as e:
            print(f"Error al guardar historal: {str(e)}")
            return False
        
    def load_conversation_histories(self):
        """
        Carga todos los historiales de conversacion desde los archivos de texto.
        Se debe llamar durante la inicializacion para recuperar las conversaciones
        almacenadas previamente.
        """

        history_dir = os.path.join(os.path.dirname(__file__), 'conversation_histories')


        if not os.path.exists(history_dir):
            print("No existe directorio de historiales")
            return
        
        for filename in os.listdir(history_dir):
            if filename.endswith('.txt'):
                session_id = filename.replace('.txt', '')
                history_file = os.path.join(history_dir,filename)

                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if session_id not in self.conversations:
                        self.conversations[session_id] = {
                            "history": [],
                            "last_context": None
                        }
                    
                    entries = content.split("--- Fin de respuesta ---\n\n")

                    for entry in entries:
                        if not entry.strip():
                            continue
                    
                        parts = entry.split("Pregunta: ",1)
                        if len(parts) < 2:
                            continue

                        timestamp_and_query = parts[1]
                        timestamp_parts = timestamp_and_query.split("\n\n",1)
                        query = timestamp_parts[0]

                        if len(timestamp_parts) < 2:
                            continue

                        response_parts = timestamp_parts[1].split("Respuesta: ",1)
                        if len(response_parts) < 2:
                            continue
                        
                        response = response_parts[1].strip()

                        existing_entries = [e["query"] for e in self.conversations[session_id]["history"]]

                        if query not in existing_entries:
                            self.conversations[session_id]["history"].append({
                                "query": query,
                                "response": response,
                                "timestamp": "Imported"
                            })
                    
                    print(f"Cargando historial para sesion {session_id} con {len(self.conversations[session_id]['history'])} entradas")
                
                except Exception as e: 
                    print(f"Error al cargar historial {filename}: {str(e)}")

    def auto_save_history(self, session_id):
        """
        Guarda automaticamente el historial despues de cada actualizacion. 
        Este metodo debe ser llamado despues de actualizar el historial de conversacion

        Args: 
            seesion_id (str): ID de la sesion cuyo historial se guardara
        """

        return self.save_conversation_history(session_id)

    def delete_conversation_history(self, session_id):
        """
        Elimina el historial de una conversacion especifica tanto de la memoria como del archivo

        Args: 
            session_id (str): ID de la sesion cuyo historial se desea eliminar

        Returns:
            bool: True si se elimino correctamente, False en lo contrario.
        """

        history_dir = os.path.join(os.path.dirname(__file__), 'conversation_histories')
        history_file = os.path.join(history_dir, f"{session_id}.txt")

        if session_id in self.conversations:
            del self.conversations[session_id]

        if os.path.exists(history_file):
            try:
                os.remove(history_file)
                return True
            except Exception as e:
                print(f"Error al eliminar archivo de historial: {str(e)}")
                return False
        return True


    """
    FUNCIONES PARA GENERAR CONTENIDO CON LA IA
    """

    def standardize_output(self, raw_response, output_type="requirements", missing_info=None):
        """
        Estandariza el formato de las respuestas de la IA para mantener consistencia.
        """
        outputs = {
            "requirements" : "REQUERIMIENTOS_GENERADOS",
            "missing_info" : "INFORMACION_INSUFICIENTE",
            "error" : "ERROR_PROCESAMIENTO"
        }
        
        status = outputs.get(output_type, "RESPUESTA_GENERAL")
        
        # Create the object with all required fields at initialization
        response_obj = RequirementResponse(
            status=status,  # Provide status when creating the object
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            content=raw_response,
            missing_info=missing_info if missing_info and isinstance(missing_info, list) else None
        )
        
        return response_obj.format_response()
        
    def setup_structured_output(self):
        """
        Cadena configurada para generar salidas estructuradas 
        """

        parser = JsonOutputParser(pydantic_object=RequirementResponse)

        format_instructions = parser.get_format_instructions()

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
            "Eres un asistente especializado en análisis de proyectos y generación de requerimientos. "
            "Debes proporcionar respuestas estructuradas según el formato especificado.\n\n"
            "Contexto adicional para tu respuesta:\n\n{context}\n\n"
            f"{format_instructions}"),
            ("human", "{input}")
        ])

        chain = prompt_template | self.llm | parser
    
        return chain

    # Método para procesar respuestas del LLM y detectar automáticamente el tipo
    def process_llm_response(self, raw_response):
        """
        Procesa la respuesta del LLM y determina automáticamente el tipo de respuesta.
        
        Args:
            raw_response (str): Respuesta original del LLM
            
        Returns:
            tuple: (output_type, processed_response, missing_info)
        """
        lower_response = raw_response.lower()
        
        # Extraer información faltante si está presente
        missing_info = None
        
        if "información insuficiente" in lower_response or "necesito más información" in lower_response:
            output_type = "missing_info"
        
            # Buscar patrones más flexibles para extraer la información faltante
            missing_pattern = re.compile(r'(?:necesito|falta)(?:.*?)(?:información|detalles)(.*?)(?:$|(?:para generar))', re.DOTALL)
            match = missing_pattern.search(lower_response)
            
            if match:
                raw_missing = match.group(1).strip()
                # Extraer elementos usando diversos patrones
                list_items = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-)\s*(.+?)(?:\n|$)', raw_missing)
                if not list_items:  # Si no hay formato de lista, intenta extraer oraciones
                    list_items = [item.strip() for item in re.split(r'(?:\.|;|\n)', raw_missing) if item.strip()]
                
                if list_items:
                    missing_info = list_items
            
        elif "error" in lower_response and ("procesar" in lower_response or "procesamiento" in lower_response):
            output_type = "error"
        else:
            output_type = "requirements"
        
        return output_type, raw_response, missing_info


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
        
        # Configurar la cadena estructurada
        parser = JsonOutputParser(pydantic_object=RequirementResponse)
        format_instructions = parser.get_format_instructions()

        # Obtenemos el historial formateado para el prompt
        history_messages = self.format_chat_history(session_id)
        
        # Creamos el prompt para el sistema de respuestas
        system_message = (
            f"{preprompt} Utiliza la información siguiente para profundizar y enriquecer tu respuesta "
            "o como una base para construir lo que se te pide:\n\n{context}\n\n"
            "Genera tu respuesta en el siguiente formato estructurado JSON. Asegúrate de incluir SIEMPRE el campo 'status':\n\n"
            f"{format_instructions.replace('{', '{{').replace('}', '}}')}\n\n"
            "IMPORTANTE: El campo 'status' es OBLIGATORIO y debe ser uno de estos valores:\n"
            "- 'REQUERIMIENTOS_GENERADOS': Cuando puedes generar requerimientos\n"
            "- 'INFORMACION_INSUFICIENTE': IMPORTANTE: Si consideras que falta información crucial para generar los requerimientos, "
            "   establece el status como 'INFORMACION_INSUFICIENTE' y proporciona una lista clara en el campo "
            "'  missing_info' con cada elemento que necesitas.\n\n"
            "- 'ERROR_PROCESAMIENTO': Cuando hay un error al procesar la solicitud\n"
            "- 'RESPUESTA_GENERAL': Para otros tipos de respuestas"
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
        response = rag_chain.invoke({
            "input": query, 
            "\"description\"": "",  # Add the missing variables
            "\"properties\"": "",
            "\"foo\"": ""
        })
        raw_answer = response.get('answer', 'No se encontró respuesta')
        
        try:
            # Intentar extraer el JSON de la respuesta
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_answer, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'({.*})', raw_answer, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # If no JSON found, fall back to manual processing
                    raise ValueError("No JSON structure found in response")
            
            # Parse the JSON and manually create a RequirementResponse
            structured_data = json.loads(json_str)
            
            # Create a complete dictionary with all required fields
            complete_data = {
                "status": "RESPUESTA_GENERAL",  # Default value
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "content": structured_data.get("content", raw_answer),
                "missing_info": structured_data.get("missing_info", None),
                "metadata": structured_data.get("metadata", None)
            }
            
            # Override with actual values from structured_data if they exist
            if "status" in structured_data:
                complete_data["status"] = structured_data["status"]
            else:
                # Determine status based on content
                content = complete_data["content"].lower()
                if "información insuficiente" in content or "necesito más información" in content:
                    complete_data["status"] = "INFORMACION_INSUFICIENTE"
                elif "error" in content:
                    complete_data["status"] = "ERROR_PROCESAMIENTO"
                elif "requerimiento" in content or "requisito" in content:
                    complete_data["status"] = "REQUERIMIENTOS_GENERADOS"
            
            if complete_data["status"] == "INFORMACION_INSUFICIENTE" and not isinstance(complete_data["missing_info"], list):
                # Si no es una lista, intentar convertir el contenido en una lista
                if isinstance(complete_data["content"], str):
                    # Extraer posibles elementos de lista del contenido
                    content_items = re.findall(r'(?:^|\n)\s*(?:\d+\.|\*|\-)\s*(.+?)(?:\n|$)', complete_data["content"])
                    if content_items:
                        complete_data["missing_info"] = content_items
                    else:
                        # Si no se pueden extraer elementos, crear una lista con un elemento genérico
                        complete_data["missing_info"] = ["Se requieren más detalles sobre el proyecto"]
            
            response_obj = RequirementResponse(**complete_data)
            standardized_answer = response_obj.format_response()
            
        except Exception as e:
            print(f"Error parsing LLM response: {str(e)}")
            # Fall back to manual processing
            output_type, processed_response, missing_info = self.process_llm_response(raw_answer)
            standardized_answer = self.standardize_output(processed_response, output_type, missing_info)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Actualizar el historial de la conversación
        self.conversations[session_id]["history"].append({
            "query": query,
            "response": standardized_answer,
            "timestamp": timestamp,
            "raw_response": raw_answer
        })
            
        # Guardar el contexto recuperado para referencia
        if "context" in response:
            self.conversations[session_id]["last_context"] = response["context"]
        
        self.auto_save_history(session_id)
        
        return standardized_answer
