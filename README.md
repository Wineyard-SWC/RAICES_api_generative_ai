# 🍇 Wineyard

<p align="center">
  <img src="https://github.com/Wineyard-SWC/RAICES/blob/main/RAICESFull.png" alt="Logo de Wineyard">
  <h3><em>"Tu equipo, tu ritmo, tu éxito."</em></h3>
</p>

[Mas sobre Wineyard](https://github.com/Wineyard-SWC/Wiki)


# 🤖 RAICES - API Generativa

**RAICES** es una API generativa diseñada para asistir en la automatización de documentación ágil mediante inteligencia artificial. Construida con **FastAPI** y potenciada por **Gemini**, **LangChain** y **ChromaDB**, esta herramienta permite crear, refinar y gestionar requerimientos, épicas e historias de usuario en **inglés** y **español**, adaptándose al contexto conversacional del proyecto.

---

## 🧠 Funcionalidades Principales

- Generación automática de requerimientos, épicas e historias de usuario.
- Aprendizaje continuo a través de RAG (Retrieval-Augmented Generation).
- Historial conversacional almacenado.
- Multilenguaje (español e inglés).
- Arquitectura extensible con IA conectada vía LangChain + Gemini + ChromaDB.

---

## 🚀 Instalación y Ejecución

1. Crear entorno virtual:
    python -m venv venv

2. Activar entorno virtual:
    - Windows: venv\Scripts\activate
    - macOS/Linux: source venv/bin/activate

3. Instalar dependencias:
    pip install -r requirements.txt

4. Ejecutar servidor:
    cd Backend
    uvicorn main:app --reload --port 8005

---

## ⚙️ Crear entorno virtual en Visual Studio Code (Windows) si no funciona lo anterior

Puedes crear el entorno virtual y preparar tu entorno de desarrollo fácilmente desde VS Code:

Abre el proyecto en Visual Studio Code.

Presiona Ctrl + Shift + P para abrir la paleta de comandos.

Escribe y selecciona:
Python: Create Environment

En las opciones:

Elige venv como tipo de entorno virtual.

Selecciona una versión válida de Python (3.7.6 o superior).

Selecciona el archivo requirements.txt cuando se te solicite.

VS Code creará el entorno virtual e instalara automáticamente las dependencias.

---


## 📬 Ejemplos de Conversación y Uso de Endpoints

### 🧾 Generación de Requerimientos

- **Endpoint**: `POST http://localhost:8005/chat`
  
```json
{
  "message": "Estoy desarrollando un sistema de punto de venta para una tienda con múltiples sucursales...",
  "session_id": ""
}
```


---

### 📚 Generación de Épicas

- **Endpoint**: `POST http://localhost:8005/generate-epics`

**Request**:
```json
{
  "requirements_description": [
    [
      {
        "id": "REQ-001",
        "title": "Registro de Productos",
        "description": "El sistema debe permitir el registro de productos con información detallada: nombre, descripción, precio, foto y categoría.",
        "category": "Funcional",
        "priority": "Alta"
      }
    ]
  ],
  "session_id": ""
}
```


---

### 🧵 Generación de Historias de Usuario

- **Endpoint**: `POST http://localhost:8005/generate-userstories`

**Request**:
```json
{
  "epic_description": {
    "content": [
      {
        "id": "EPIC-001",
        "title": "Gestión Integral de Productos",
        "description": "Permitir la creación, visualización, modificación y eliminación de productos..."
      }
    ]
  },
  "session_id": ""
}
```




## 💬 Ejemplo de Conversación con la IA

Para revisar una conversación completa con prompts de entrada y las respuestas de la IA (incluyendo requerimientos, épicas e historias generadas), consulta el archivo:

**Requerimientos generados**  
[➡️ requerimientos.json](./requerimientos.json)

**Épicas generadas**  
[➡️ epicas.json](./epicas.json)

**Historias de usuario generadas**  
[➡️ historias_usuario.json](./historias_usuario.json)

---

### 📨 Ejemplos de Requests

**Request para generación de épicas**  
[➡️ request_requerimientos.json](./request_requerimientos.json)

**Request para generación de historias de usuario**  
[➡️ request_userstories.json](./request_userstories.json)

## 📜 Licencia

Este proyecto está licenciado bajo la **Licencia MIT**. Revisa el archivo `LICENSE.md` para más información.

## 👥Autores


- ⭐ [Raymundo Daniel Medina Arzola](https://github.com/RayMedArz) | **Product Owner** | **Especialista en Bases de Datos**
- 👑 [Fernando Espidio Santamaría](https://github.com/FernandoEspidio) | **SCRUM Master** | **QA Tester**
- 🎩 [Alejandro Negrete Pasaye](https://github.com/Alekstremo) | **Back-end Developer** |
- 🎩 [Oscar Zhao Xu](https://github.com/Oscar21122) | **Full-stack Developer** |
- 🎩 [Louis Loewen Salas](https://github.com/louisloewen) | **Front-end Developer** |
- 🎩 [Abdiel Fritsche Barajas](https://github.com/AbdielFritsche) | **Back-end Developer**


