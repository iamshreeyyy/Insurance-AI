import streamlit as st
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
WEBHOOK_URL = "http://localhost:8000/hackrx/run"
BEARER_TOKEN = "b37bee837667836f35b77319b6c7b1f712a2955869766b98de9400065a1c2c7f"

def call_hackrx_webhook(pdf_url: str, questions: list):
    """Call the HackRX webhook with PDF URL and questions"""
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "documents": pdf_url,
        "questions": questions
    }
    
    try:
        with st.spinner("Processing your request..."):
            response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=300)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to the webhook. Make sure it's running on localhost:8000")
        return None
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out. The processing took too long.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="HackRX Insurance AI Demo",
        page_icon="🛡️",
        layout="wide"
    )
    
    st.title("🛡️ HackRX Insurance AI Webhook Demo")
    st.markdown("Test the insurance policy analysis webhook with PDF documents")
    
    # Sidebar with instructions
    with st.sidebar:
        st.header("ℹ️ Instructions")
        st.markdown("""
        1. **Start the webhook**: Run `python hackrx_webhook_simple.py`
        2. **Enter PDF URL**: Paste the blob URL of your insurance policy
        3. **Add questions**: Enter questions about the policy
        4. **Submit**: Get AI-powered answers
        """)
        
        st.header("🔗 Webhook Info")
        st.code(f"URL: {WEBHOOK_URL}")
        st.code(f"Token: {BEARER_TOKEN}")
        
        st.header("🧪 Test Data")
        if st.button("Load Sample Data"):
            st.session_state.sample_loaded = True
    
    # Main interface
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📄 Document Input")
        
        # Check if sample data should be loaded
        if st.session_state.get('sample_loaded', False):
            default_url = "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D"
        else:
            default_url = ""
        
        pdf_url = st.text_input(
            "PDF Blob URL:",
            value=default_url,
            help="Enter the full URL to your PDF document"
        )
        
        st.header("❓ Questions")
        
        # Sample questions if loaded
        if st.session_state.get('sample_loaded', False):
            default_questions = [
                "What is the grace period for premium payment under the National Parivar Mediclaim Plus Policy?",
                "What is the waiting period for pre-existing diseases (PED) to be covered?",
                "Does this policy cover maternity expenses, and what are the conditions?",
                "What is the waiting period for cataract surgery?",
                "Are the medical expenses for an organ donor covered under this policy?"
            ]
        else:
            default_questions = [""]
        
        questions = []
        for i in range(10):  # Allow up to 10 questions
            if i < len(default_questions):
                default_q = default_questions[i]
            else:
                default_q = ""
                
            question = st.text_input(f"Question {i+1}:", value=default_q, key=f"q{i}")
            if question.strip():
                questions.append(question.strip())
        
        # Submit button
        if st.button("🚀 Analyze Document", type="primary", use_container_width=True):
            if not pdf_url.strip():
                st.error("Please enter a PDF URL")
            elif not questions:
                st.error("Please enter at least one question")
            else:
                # Store the request in session state
                st.session_state.last_request = {
                    "pdf_url": pdf_url,
                    "questions": questions
                }
                st.session_state.processing = True
    
    with col2:
        st.header("🤖 AI Responses")
        
        # Process the request if needed
        if st.session_state.get('processing', False):
            request_data = st.session_state.last_request
            
            # Call the webhook
            result = call_hackrx_webhook(request_data["pdf_url"], request_data["questions"])
            
            if result and "answers" in result:
                st.success(f"✅ Processed {len(result['answers'])} questions successfully!")
                
                # Display Q&A pairs
                for i, (question, answer) in enumerate(zip(request_data["questions"], result["answers"]), 1):
                    with st.expander(f"Q{i}: {question}", expanded=True):
                        st.write(answer)
                        
                # Store results and clear processing flag
                st.session_state.last_result = result
                st.session_state.processing = False
                
                # Show JSON response
                with st.expander("📋 Raw JSON Response"):
                    st.json(result)
            else:
                st.session_state.processing = False
        
        # Show previous results if available
        elif st.session_state.get('last_result'):
            result = st.session_state.last_result
            request_data = st.session_state.last_request
            
            st.info(f"Previous result: {len(result['answers'])} answers")
            
            for i, (question, answer) in enumerate(zip(request_data["questions"], result["answers"]), 1):
                with st.expander(f"Q{i}: {question}"):
                    st.write(answer)
        
        else:
            st.info("Enter a PDF URL and questions, then click 'Analyze Document' to get started.")
    
    # Footer
    st.markdown("---")
    st.markdown("**HackRX Insurance AI Webhook Demo** | Built with Streamlit & FastAPI")

if __name__ == "__main__":
    main()
