import streamlit as st
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
groq_api_key = os.environ['GROQ_API_KEY']

# Set up custom CSS
def set_custom_css():
    st.markdown("""
    <style>
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .stTextInput input {
            border-radius: 20px;
            padding: 10px 15px;
        }
        .chat-message {
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .user-message {
            background: #ffffff;
            border: 1px solid #e0e0e0;
        }
        .bot-message {
            background: #007bff;
            color: white;
        }
        .stMarkdown table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        .stMarkdown th {
            background-color: #007bff;
            color: white;
        }
        .stMarkdown td, .stMarkdown th {
            padding: 12px;
            border: 1px solid #ddd;
            text-align: left;
        }
    </style>
    """, unsafe_allow_html=True)

# Initialize agents
def initialize_insurance_agents():
    life_insurance_agent = Agent(
        name="Life Insurance Specialist",
        role="Execute research and analysis on life insurance products, underwriting standards, and mortality risk factors",
        description="""Certified life insurance expert specializing in:
        - Policy comparisons (term/whole/universal life)
        - Medical underwriting and risk assessment
        - Premium calculation methodologies
        - Regulatory compliance (SOA, ACLI standards)
        Maintains up-to-date knowledge of IRS tax treatment of life insurance products""",
        model=Groq(id="llama-3.3-70b-versatile", api_key=groq_api_key, temperature=0.2, max_retries=2),
        tools=[DuckDuckGoTools()],
        instructions="""STRICT PROTOCOLS:
        1. Only respond to life insurance queries
        2. Reject with template: "I specialize exclusively in life insurance. For [queried topic], please consult a [relevant expert]."
        3. Always cite sources for premium/benefit comparisons
        4. Flag outdated regulations automatically""",
        show_tool_calls=True,
        markdown=True,
    )

    home_insurance_agent = Agent(
        name="Home Insurance Specialist",
        role="Analyze property insurance coverages, claims processes, and regional risk factors",
        description="""Licensed property insurance advisor with expertise in:
        - HO-3 vs HO-5 policy structures
        - Catastrophic loss modeling (flood, earthquake, wildfire)
        - Replacement cost vs actual cash value
        - FAIR Plan eligibility requirements""",
        model=Groq(id="llama3-70b-8192", api_key=groq_api_key, temperature=0.2, max_retries=2),
        tools=[DuckDuckGoTools()],
        instructions="""STRICT PROTOCOLS:
        1. Domain-limited to residential/commercial property coverage
        2. Rejection template: "As a property insurance specialist, I cannot advise on [queried topic]."
        3. Always disclose coverage exclusions
        4. Cross-reference with NFIP data for flood-related queries""",
        show_tool_calls=True,
        markdown=True,
    )

    auto_insurance_agent = Agent(
        name="Auto Insurance Specialist",
        role="Process vehicle insurance inquiries with emphasis on state-specific compliance",
        description="""ASE-certified auto insurance analyst covering:
        - Comparative fault state regulations
        - Telematics and usage-based insurance
        - Total loss threshold calculations
        - Rideshare endorsement requirements""",
        model=Groq(id="llama3-70b-8192", api_key=groq_api_key, temperature=0.2, max_retries=2),
        tools=[DuckDuckGoTools()],
        instructions="""STRICT PROTOCOLS:
        1. Only address motor vehicle insurance topics
        2. Rejection template: "This query about [topic] falls outside my auto insurance specialization."
        3. Always verify state DOI regulations
        4. Disclose claim impact on premiums""",
        show_tool_calls=True,
        markdown=True,
    )

    return Agent(
        name="Insurance Team Coordinator",
        role="Route inquiries to appropriate insurance specialists and enforce domain boundaries",
        description="""Master routing system for insurance-related queries that:
        - Validates question relevance to insurance domain
        - Maintains audit trails of specialist assignments
        - Enforces FINRA-style suitability standards
        - Implements fallback protocols for cross-domain queries""",
        team=[life_insurance_agent, home_insurance_agent, auto_insurance_agent],
        model=Groq(id="llama3-70b-8192", api_key=groq_api_key, temperature=0.2, max_retries=2),
        instructions="""DOMAIN CONTROL SYSTEM:
        1. First-layer filter: Reject non-insurance queries with:
           "Our specialists only handle insurance matters. Your query about [topic] is outside our scope."
        
        2. Routing matrix:
           - Life: Mortality risk/policy illustrations → Life Specialist
           - Property: Dwelling coverage/CLUE reports → Home Specialist
           - Vehicle: SR-22 filings/UM coverage → Auto Specialist
        
        3. Compliance checks:
           - Verify no financial advice beyond insurance products
           - Block health/legal disguised queries
           - Log all rejections with reason codes""",
        show_tool_calls=True,
        markdown=True,
    )

# Streamlit app
def main():
    set_custom_css()
    
    st.title("🛡️ Insurance Specialist Assistant")
    st.markdown("""
    Welcome to your AI-powered insurance advisory system! Our certified specialists can help with:
    - 🏠 Homeowners/Property insurance coverage analysis
    - 🚗 Auto insurance policy comparisons
    - 💼 Life insurance underwriting guidance
    - ⚖️ Claims process explanations
    """)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)
    
    # Get user input
    if prompt := st.chat_input("Ask your insurance question..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Initialize insurance agent team
        insurance_team = initialize_insurance_agents()
        
        # Generate response
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""
            
            try:
                # First verify if the query is insurance-related
                if not is_insurance_related(prompt):
                    full_response = """🚫 <span style="color:red">Insurance Domain Restriction</span>
                    
Our specialists only handle insurance-related inquiries. Your question about: 
'<i>{}</i>' 
falls outside our scope. 

Please consult appropriate professionals for:
- Financial planning → Certified Financial Planner
- Legal matters → Attorney
- Health advice → Medical Practitioner""".format(prompt[:100] + ("..." if len(prompt) > 100 else ""))
                else:
                    # Get the response from the insurance team
                    response = insurance_team.run(prompt)
                    
                    # Extract the content from the response
                    if hasattr(response, 'content'):
                        response_content = response.content
                    else:
                        response_content = str(response)
                    
                    # Simulate streaming effect
                    for i in range(0, len(response_content), 5):
                        chunk = response_content[:i+5]
                        response_container.markdown(chunk + "▌", unsafe_allow_html=True)
                        time.sleep(0.02)
                    
                    full_response = response_content

            except Exception as e:
                full_response = f"""⚠️ <span style="color:orange">Insurance Advisory System Error</span>
                
Our specialists encountered an issue processing your insurance query:
<code>{str(e)}</code>

Please rephrase your question or try again later."""
            
            # Display final response
            response_container.markdown(full_response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

def is_insurance_related(prompt: str) -> bool:
    """Check if the user query is insurance-related"""
    insurance_keywords = {
        'life': ['life insurance', 'term life', 'whole life', 'death benefit', 'underwriting'],
        'home': ['home insurance', 'property insurance', 'dwelling coverage', 'HO-3', 'HO-5'],
        'auto': ['auto insurance', 'car insurance', 'liability coverage', 'collision', 'comprehensive']
    }
    prompt_lower = prompt.lower()
    return any(
        keyword in prompt_lower 
        for category in insurance_keywords.values() 
        for keyword in category
    )

if __name__ == "__main__":
    main()