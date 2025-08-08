from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import requests
import tempfile
import os
from dotenv import load_dotenv
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Agno imports
from agno.embedder.openai import OpenAIEmbedder
from agno.agent import Agent, RunResponse
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.chroma import ChromaDb
from agno.document.chunking.document import DocumentChunking
from agno.models.google import Gemini
from agno.memory.v2 import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.storage.sqlite import SqliteStorage

load_dotenv()

# Environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Expected bearer token for authentication
EXPECTED_BEARER_TOKEN = "b37bee837667836f35b77319b6c7b1f712a2955869766b98de9400065a1c2c7f"

# FastAPI app
app = FastAPI(
    title="HackRX Insurance AI API",
    description="Insurance AI webhook for HackRX submission",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# Request/Response models
class HackRXRequest(BaseModel):
    documents: HttpUrl  # PDF blob URL
    questions: List[str]  # List of questions to answer

class HackRXResponse(BaseModel):
    answers: List[str]

# Authentication dependency
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != EXPECTED_BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Global variables for agent components
agent_storage = None
memory_db = None
openai_embedder = None
agent = None

def initialize_agent_components():
    """Initialize agent components globally"""
    global agent_storage, memory_db, openai_embedder, agent
    
    try:
        # Create storage directories
        os.makedirs("database_files", exist_ok=True)
        os.makedirs("temp_knowledge", exist_ok=True)
        
        agent_storage = SqliteStorage(
            table_name="hackrx_agent_sessions",
            db_file="database_files/hackrx_agent_storage.db",
            auto_upgrade_schema=True,
        )

        memory_db = SqliteMemoryDb(
            table_name="hackrx_memories",
            db_file="database_files/hackrx_memory.db",
        )

        openai_embedder = OpenAIEmbedder(
            id="text-embedding-3-large", 
            api_key=OPENAI_API_KEY
        )
        
        print("Agent components initialized successfully")
        
    except Exception as e:
        print(f"Error initializing agent components: {e}")
        raise

def download_pdf_from_url(url: str, temp_dir: str) -> str:
    """Download PDF from blob URL and save to temp directory"""
    try:
        # Download the PDF
        response = requests.get(str(url), timeout=30)
        response.raise_for_status()
        
        # Save to temp file
        pdf_path = os.path.join(temp_dir, "document.pdf")
        with open(pdf_path, "wb") as f:
            f.write(response.content)
            
        print(f"PDF downloaded successfully to {pdf_path}")
        return pdf_path
        
    except requests.RequestException as e:
        print(f"Error downloading PDF: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to download PDF from URL: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error downloading PDF: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal error downloading PDF: {str(e)}"
        )

def create_knowledge_base_from_pdf(pdf_path: str, temp_dir: str) -> PDFKnowledgeBase:
    """Create a knowledge base from downloaded PDF"""
    try:
        # Create knowledge base with the PDF
        knowledge_base = PDFKnowledgeBase(
            path=os.path.dirname(pdf_path),  # Directory containing the PDF
            vector_db=ChromaDb(
                collection="hackrx_insurance_kb",
                path=os.path.join(temp_dir, "chroma_db"),
                persistent_client=True,
                embedder=openai_embedder
            ),
            chunking_strategy=DocumentChunking(),
        )
        
        # Load the knowledge base
        knowledge_base.load(recreate=True, skip_existing=False)
        print("Knowledge base created and loaded successfully")
        
        return knowledge_base
        
    except Exception as e:
        print(f"Error creating knowledge base: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create knowledge base: {str(e)}"
        )

def create_agent_with_knowledge(knowledge_base: PDFKnowledgeBase, session_id: str) -> Agent:
    """Create an agent with the given knowledge base"""
    try:
        # Insurance-specific agent instructions
        agent_instructions = """
You are an expert insurance AI assistant specialized in analyzing insurance policies and answering questions about coverage, terms, and conditions.

Instructions:
1. Always search the knowledge base first to find relevant information
2. Provide accurate, specific answers based on the policy documents
3. If information is not available in the documents, clearly state this
4. Be precise with policy details like waiting periods, coverage amounts, exclusions, etc.
5. Use clear, professional language
6. For numerical values (amounts, percentages, time periods), be exact
7. When referencing policy sections or clauses, be specific

Focus on providing direct, factual answers based solely on the provided insurance policy documents.
"""
        
        agent = Agent(
            model=Gemini(id="gemini-2.0-flash", api_key=GOOGLE_API_KEY),
            memory=Memory(db=memory_db),
            storage=agent_storage,
            knowledge=knowledge_base,
            search_knowledge=True,
            show_tool_calls=False,
            add_history_to_messages=False,
            num_history_runs=1,
            num_history_responses=1,
            enable_user_memories=False,
            enable_session_summaries=False,
            read_chat_history=False,
            read_tool_call_history=False,
            enable_agentic_memory=False,
            debug_mode=False,
            instructions=agent_instructions,
            session_id=session_id,
        )
        
        print("Agent created successfully")
        return agent
        
    except Exception as e:
        print(f"Error creating agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create agent: {str(e)}"
        )

def process_question_with_agent(agent: Agent, question: str, question_idx: int) -> str:
    """Process a single question with the agent"""
    try:
        print(f"Processing question {question_idx + 1}: {question}")
        
        # Run the agent with the question
        response: RunResponse = agent.run(question, user_id=f"hackrx_user_{question_idx}")
        
        if response and hasattr(response, 'content'):
            answer = response.content.strip()
            print(f"Answer {question_idx + 1}: {answer[:100]}...")
            return answer
        else:
            print(f"Warning: No content in response for question {question_idx + 1}")
            return "I couldn't find specific information about this in the policy documents."
            
    except Exception as e:
        print(f"Error processing question {question_idx + 1}: {e}")
        return f"Error processing question: {str(e)}"

@app.post("/hackrx/run", response_model=HackRXResponse)
async def hackrx_run(
    request: HackRXRequest,
    token: str = Depends(verify_token)
):
    """
    Main endpoint for processing insurance policy questions
    """
    temp_dir = None
    try:
        print(f"Received request with {len(request.questions)} questions")
        print(f"Document URL: {request.documents}")
        
        # Create temporary directory for this request
        temp_dir = tempfile.mkdtemp(prefix="hackrx_")
        print(f"Created temp directory: {temp_dir}")
        
        # Download PDF from blob URL
        pdf_path = download_pdf_from_url(request.documents, temp_dir)
        
        # Create knowledge base from PDF
        knowledge_base = create_knowledge_base_from_pdf(pdf_path, temp_dir)
        
        # Create agent with knowledge base
        session_id = f"hackrx_session_{hash(str(request.documents))}"
        agent = create_agent_with_knowledge(knowledge_base, session_id)
        
        # Process all questions
        answers = []
        
        # Use ThreadPoolExecutor for parallel processing of questions
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_question_with_agent, agent, question, idx)
                for idx, question in enumerate(request.questions)
            ]
            
            # Collect results in order
            for future in futures:
                try:
                    answer = future.result(timeout=60)  # 60 second timeout per question
                    answers.append(answer)
                except Exception as e:
                    print(f"Error in future result: {e}")
                    answers.append("Error processing this question.")
        
        print(f"Processed {len(answers)} answers successfully")
        
        return HackRXResponse(answers=answers)
        
    except HTTPException:
        raise
    except Exception as e:
        error_message = traceback.format_exc()
        print(f"Unexpected error in hackrx_run: {error_message}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                print(f"Error cleaning up temp directory: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "HackRX Insurance AI API is running"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HackRX Insurance AI API",
        "version": "1.0.0",
        "endpoints": {
            "main": "POST /hackrx/run",
            "health": "GET /health"
        }
    }

# Initialize components on startup
@app.on_event("startup")
async def startup_event():
    """Initialize agent components on startup"""
    try:
        initialize_agent_components()
        print("FastAPI app started successfully")
    except Exception as e:
        print(f"Failed to initialize app: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    
    print("Starting HackRX Insurance AI API...")
    uvicorn.run(
        "hackrx_webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
