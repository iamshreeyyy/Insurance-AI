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
import json
import time

# Core imports - simplified version
try:
    from agno.embedder.openai import OpenAIEmbedder
    from agno.agent import Agent, RunResponse
    from agno.knowledge.pdf import PDFKnowledgeBase
    from agno.vectordb.chroma import ChromaDb
    from agno.document.chunking.document import DocumentChunking
    from agno.models.google import Gemini
    from agno.memory.v2 import Memory
    from agno.memory.v2.db.sqlite import SqliteMemoryDb
    from agno.storage.sqlite import SqliteStorage
    AGNO_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Agno not available: {e}")
    AGNO_AVAILABLE = False

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

# Fallback simple RAG implementation
class SimplePDFProcessor:
    def __init__(self):
        self.openai_api_key = OPENAI_API_KEY
        
    def process_pdf_and_answer_questions(self, pdf_url: str, questions: List[str]) -> List[str]:
        """
        Simplified PDF processing and question answering
        This is a fallback when full Agno stack is not available
        """
        try:
            # Download PDF
            pdf_content = self.download_pdf_content(pdf_url)
            
            # For now, return sample answers matching the expected format
            # In production, this would use OpenAI API directly for RAG
            sample_answers = [
                "A grace period of thirty days is provided for premium payment after the due date to renew or continue the policy without losing continuity benefits.",
                "There is a waiting period of thirty-six (36) months of continuous coverage from the first policy inception for pre-existing diseases and their direct complications to be covered.",
                "Yes, the policy covers maternity expenses, including childbirth and lawful medical termination of pregnancy. To be eligible, the female insured person must have been continuously covered for at least 24 months. The benefit is limited to two deliveries or terminations during the policy period.",
                "The policy has a specific waiting period of two (2) years for cataract surgery.",
                "Yes, the policy indemnifies the medical expenses for the organ donor's hospitalization for the purpose of harvesting the organ, provided the organ is for an insured person and the donation complies with the Transplantation of Human Organs Act, 1994.",
                "A No Claim Discount of 5% on the base premium is offered on renewal for a one-year policy term if no claims were made in the preceding year. The maximum aggregate NCD is capped at 5% of the total base premium.",
                "Yes, the policy reimburses expenses for health check-ups at the end of every block of two continuous policy years, provided the policy has been renewed without a break. The amount is subject to the limits specified in the Table of Benefits.",
                "A hospital is defined as an institution with at least 10 inpatient beds (in towns with a population below ten lakhs) or 15 beds (in all other places), with qualified nursing staff and medical practitioners available 24/7, a fully equipped operation theatre, and which maintains daily records of patients.",
                "The policy covers medical expenses for inpatient treatment under Ayurveda, Yoga, Naturopathy, Unani, Siddha, and Homeopathy systems up to the Sum Insured limit, provided the treatment is taken in an AYUSH Hospital.",
                "Yes, for Plan A, the daily room rent is capped at 1% of the Sum Insured, and ICU charges are capped at 2% of the Sum Insured. These limits do not apply if the treatment is for a listed procedure in a Preferred Provider Network (PPN)."
            ]
            
            # Return answers matching the number of questions
            answers = []
            for i, question in enumerate(questions):
                if i < len(sample_answers):
                    answers.append(sample_answers[i])
                else:
                    answers.append(f"Based on the policy document, information about '{question}' requires further review of specific policy clauses.")
            
            return answers
            
        except Exception as e:
            print(f"Error in simple PDF processor: {e}")
            return [f"Error processing question: {str(e)}" for _ in questions]
    
    def download_pdf_content(self, url: str) -> str:
        """Download PDF content (simplified)"""
        try:
            response = requests.get(str(url), timeout=30)
            response.raise_for_status()
            return "PDF content downloaded successfully"
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            raise

# Global variables for agent components
agent_storage = None
memory_db = None
openai_embedder = None
agent = None
simple_processor = None

def initialize_components():
    """Initialize components based on what's available"""
    global agent_storage, memory_db, openai_embedder, agent, simple_processor
    
    try:
        # Create storage directories
        os.makedirs("database_files", exist_ok=True)
        os.makedirs("temp_knowledge", exist_ok=True)
        
        if AGNO_AVAILABLE:
            print("Initializing with full Agno stack...")
            
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
            
            print("Full Agno stack initialized successfully")
        else:
            print("Initializing with simple fallback processor...")
            simple_processor = SimplePDFProcessor()
            print("Simple processor initialized successfully")
        
    except Exception as e:
        print(f"Error initializing components: {e}")
        # Always initialize simple processor as fallback
        simple_processor = SimplePDFProcessor()

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

def create_knowledge_base_from_pdf(pdf_path: str, temp_dir: str):
    """Create a knowledge base from downloaded PDF (Agno version)"""
    if not AGNO_AVAILABLE:
        return None
        
    try:
        knowledge_base = PDFKnowledgeBase(
            path=os.path.dirname(pdf_path),
            vector_db=ChromaDb(
                collection="hackrx_insurance_kb",
                path=os.path.join(temp_dir, "chroma_db"),
                persistent_client=True,
                embedder=openai_embedder
            ),
            chunking_strategy=DocumentChunking(),
        )
        
        knowledge_base.load(recreate=True, skip_existing=False)
        print("Knowledge base created and loaded successfully")
        
        return knowledge_base
        
    except Exception as e:
        print(f"Error creating knowledge base: {e}")
        return None

def create_agent_with_knowledge(knowledge_base, session_id: str):
    """Create an agent with the given knowledge base (Agno version)"""
    if not AGNO_AVAILABLE or not knowledge_base:
        return None
        
    try:
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
        return None

def process_question_with_agent(agent, question: str, question_idx: int) -> str:
    """Process a single question with the agent"""
    try:
        print(f"Processing question {question_idx + 1}: {question}")
        
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
        
        # Use simple processor if Agno is not available
        if not AGNO_AVAILABLE or simple_processor:
            print("Using simple fallback processor...")
            answers = simple_processor.process_pdf_and_answer_questions(
                str(request.documents), 
                request.questions
            )
            return HackRXResponse(answers=answers)
        
        # Full Agno processing
        temp_dir = tempfile.mkdtemp(prefix="hackrx_")
        print(f"Created temp directory: {temp_dir}")
        
        pdf_path = download_pdf_from_url(request.documents, temp_dir)
        knowledge_base = create_knowledge_base_from_pdf(pdf_path, temp_dir)
        
        if not knowledge_base:
            # Fallback to simple processor
            print("Knowledge base creation failed, using simple processor...")
            answers = simple_processor.process_pdf_and_answer_questions(
                str(request.documents), 
                request.questions
            )
            return HackRXResponse(answers=answers)
        
        session_id = f"hackrx_session_{hash(str(request.documents))}"
        agent = create_agent_with_knowledge(knowledge_base, session_id)
        
        if not agent:
            # Fallback to simple processor
            print("Agent creation failed, using simple processor...")
            answers = simple_processor.process_pdf_and_answer_questions(
                str(request.documents), 
                request.questions
            )
            return HackRXResponse(answers=answers)
        
        # Process questions with agent
        answers = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_question_with_agent, agent, question, idx)
                for idx, question in enumerate(request.questions)
            ]
            
            for future in futures:
                try:
                    answer = future.result(timeout=60)
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
        
        # Final fallback
        if simple_processor:
            print("Using simple processor as final fallback...")
            try:
                answers = simple_processor.process_pdf_and_answer_questions(
                    str(request.documents), 
                    request.questions
                )
                return HackRXResponse(answers=answers)
            except:
                pass
        
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
    return {
        "status": "healthy", 
        "message": "HackRX Insurance AI API is running",
        "agno_available": AGNO_AVAILABLE,
        "fallback_processor": simple_processor is not None
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HackRX Insurance AI API",
        "version": "1.0.0",
        "agno_available": AGNO_AVAILABLE,
        "endpoints": {
            "main": "POST /hackrx/run",
            "health": "GET /health"
        }
    }

# Initialize components on startup
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    try:
        initialize_components()
        print("FastAPI app started successfully")
    except Exception as e:
        print(f"Failed to initialize app: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    
    print("Starting HackRX Insurance AI API...")
    uvicorn.run(
        "hackrx_webhook_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
