import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

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
        with st.spinner("🔄 Processing your insurance policy questions..."):
            response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=300)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Could not connect to the webhook. Make sure it's running on localhost:8000")
        st.info("💡 Start the webhook by running: `python hackrx_webhook_minimal.py`")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. The processing took too long.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def load_sample_data():
    """Load the HackRX sample data"""
    st.session_state.sample_url = "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D"
    st.session_state.sample_questions = [
        "What is the grace period for premium payment under the National Parivar Mediclaim Plus Policy?",
        "What is the waiting period for pre-existing diseases (PED) to be covered?",
        "Does this policy cover maternity expenses, and what are the conditions?",
        "What is the waiting period for cataract surgery?",
        "Are the medical expenses for an organ donor covered under this policy?",
        "What is the No Claim Discount (NCD) offered in this policy?",
        "Is there a benefit for preventive health check-ups?",
        "How does the policy define a 'Hospital'?",
        "What is the extent of coverage for AYUSH treatments?",
        "Are there any sub-limits on room rent and ICU charges for Plan A?"
    ]

def main():
    st.set_page_config(
        page_title="HackRX Insurance AI Demo",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        color: #e0e0e0;
        margin: 0.5rem 0 0 0;
        font-size: 1.2rem;
    }
    .stButton > button {
        width: 100%;
        background: #2a5298;
        color: white;
        border: none;
        padding: 0.75rem;
        border-radius: 5px;
        font-size: 1.1rem;
        margin-top: 1rem;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🛡️ HackRX Insurance AI Demo</h1>
        <p>AI-powered Insurance Policy Analysis Webhook</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ Instructions")
        st.markdown("""
        ### How to Use:
        1. **Start Webhook**: Run the webhook server first
        2. **Enter PDF URL**: Insurance policy document
        3. **Add Questions**: Ask about policy details
        4. **Get Answers**: AI analyzes and responds
        """)
        
        st.header("🔧 Webhook Status")
        if st.button("🔍 Check Webhook Status"):
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    st.success("✅ Webhook is running!")
                    st.json(data)
                else:
                    st.error("❌ Webhook not responding")
            except:
                st.error("❌ Webhook not running")
                st.info("Start with: `python hackrx_webhook_minimal.py`")
        
        st.header("🧪 Sample Data")
        if st.button("📋 Load HackRX Test Case"):
            load_sample_data()
            st.success("✅ Sample data loaded!")
            st.rerun()
        
        st.header("📊 API Details")
        st.code(f"URL: {WEBHOOK_URL}")
        st.code("Method: POST")
        st.code("Auth: Bearer Token")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📄 Document & Questions")
        
        # PDF URL input
        pdf_url = st.text_input(
            "📎 Insurance Policy PDF URL:",
            value=st.session_state.get('sample_url', ''),
            help="Enter the complete URL to your PDF document"
        )
        
        st.header("❓ Questions to Ask")
        
        # Questions input
        questions = []
        sample_questions = st.session_state.get('sample_questions', [''] * 10)
        
        for i in range(10):
            default_value = sample_questions[i] if i < len(sample_questions) else ''
            question = st.text_area(
                f"Question {i+1}:",
                value=default_value,
                height=60,
                key=f"question_{i}",
                help=f"Enter question {i+1} about the insurance policy"
            )
            if question.strip():
                questions.append(question.strip())
        
        # Submit button
        col_submit, col_clear = st.columns([2, 1])
        
        with col_submit:
            if st.button("🚀 Analyze Insurance Policy", type="primary"):
                if not pdf_url.strip():
                    st.error("📎 Please enter a PDF URL")
                elif not questions:
                    st.error("❓ Please enter at least one question")
                else:
                    st.session_state.processing = True
                    st.session_state.current_request = {
                        "pdf_url": pdf_url,
                        "questions": questions
                    }
                    st.rerun()
        
        with col_clear:
            if st.button("🗑️ Clear All"):
                for key in list(st.session_state.keys()):
                    if key.startswith('question_') or key in ['sample_url', 'sample_questions', 'processing', 'current_request', 'last_result']:
                        del st.session_state[key]
                st.rerun()
    
    with col2:
        st.header("🤖 AI Analysis Results")
        
        # Process request if needed
        if st.session_state.get('processing', False):
            request_data = st.session_state.current_request
            
            # Show request info
            with st.expander("📋 Request Details", expanded=True):
                st.write(f"**Document**: {request_data['pdf_url'][:100]}...")
                st.write(f"**Questions**: {len(request_data['questions'])} questions")
            
            # Call webhook
            result = call_hackrx_webhook(request_data["pdf_url"], request_data["questions"])
            
            if result and "answers" in result:
                st.markdown("""
                <div class="success-box">
                    ✅ <strong>Analysis Completed Successfully!</strong><br>
                    🎯 All questions have been processed and answered.
                </div>
                """, unsafe_allow_html=True)
                
                # Display Q&A pairs
                st.subheader("💬 Questions & Answers")
                for i, (question, answer) in enumerate(zip(request_data["questions"], result["answers"]), 1):
                    with st.expander(f"Q{i}: {question[:80]}..." if len(question) > 80 else f"Q{i}: {question}", expanded=i <= 3):
                        st.write("**Question:**")
                        st.info(question)
                        st.write("**Answer:**")
                        st.success(answer)
                
                # Store results and clear processing flag
                st.session_state.last_result = result
                st.session_state.processing = False
                
                # Show raw response
                with st.expander("🔧 Raw JSON Response"):
                    st.json(result)
            else:
                st.session_state.processing = False
        
        # Show previous results if available
        elif st.session_state.get('last_result'):
            result = st.session_state.last_result
            request_data = st.session_state.current_request
            
            st.info("📋 Previous analysis results (click 'Analyze' to run new analysis)")
            
            with st.expander("💬 View Previous Results", expanded=True):
                for i, (question, answer) in enumerate(zip(request_data["questions"], result["answers"]), 1):
                    st.write(f"**Q{i}:** {question}")
                    st.write(f"**A{i}:** {answer}")
                    st.divider()
        
        else:
            st.info("👆 Enter a PDF URL and questions above, then click 'Analyze Insurance Policy' to get started.")
            
            # Show sample expected output
            st.subheader("📋 Expected Output Format")
            sample_output = {
                "answers": [
                    "A grace period of thirty days is provided for premium payment...",
                    "There is a waiting period of thirty-six (36) months...",
                    "Yes, the policy covers maternity expenses..."
                ]
            }
            st.json(sample_output)
    
    # Footer
    st.markdown("---")
    col_footer1, col_footer2, col_footer3 = st.columns([1, 1, 1])
    
    with col_footer1:
        st.markdown("**🔗 Webhook Endpoint**")
        st.code("POST /hackrx/run")
    
    with col_footer2:
        st.markdown("**🔑 Authentication**")
        st.code("Bearer Token")
    
    with col_footer3:
        st.markdown("**⚡ Response Time**")
        st.code("~2.5 seconds")

if __name__ == "__main__":
    main()
