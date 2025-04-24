from typing import Optional, List
from agno.embedder.openai import OpenAIEmbedder
from agno.agent import Agent, RunResponse
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.milvus import Milvus
from agno.document.chunking.document import DocumentChunking
from agno.storage.postgres import PostgresStorage
from agno.models.google import Gemini
from flask import Flask, request, jsonify
import traceback

import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PG_DB_URL = os.getenv("PG_DB_URL")
storage = PostgresStorage(table_name="agent_sessions", db_url=PG_DB_URL,auto_upgrade_schema=True)

# Initialize Milvus vector database
milvus_uri = "http://localhost:19530"
openai_embedder = OpenAIEmbedder(id="text-embedding-3-large", api_key=OPENAI_API_KEY)

local_pdf_knowledge_base = PDFKnowledgeBase(
    path="insurance_data_strings.pdf",
    vector_db=Milvus(
        collection="insurance_customers_details",
        uri=milvus_uri,
        embedder=openai_embedder
    ),
)

url_pdf_knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://www.iii.org/sites/default/files/docs/pdf/Insurance_Handbook_20103.pdf"],
    vector_db=Milvus(
        collection="insurance_details_handbook",
        uri=milvus_uri,
        # token="your_token", # Uncomment and replace if your Milvus has authentication
        embedder=openai_embedder
    ),
    chunking_strategy=DocumentChunking(),
)

knowledge_base = CombinedKnowledgeBase(
    sources=[
        local_pdf_knowledge_base,
        url_pdf_knowledge_base,
    ],
    vector_db=Milvus(
        collection="combined_knowledge",
        uri=milvus_uri,
        embedder=openai_embedder 
    ),
)

agent = Agent(
    model=Gemini(id="gemini-2.0-flash", api_key=GOOGLE_API_KEY),
    session_id="fixed_id_for_demo", # Consider making this dynamic per user
    storage=storage,
    user_id="api_user", # Consider making this dynamic per user
    knowledge=knowledge_base,
    search_knowledge=True,
    show_tool_calls=True,
    add_history_to_messages=True,
    num_history_runs=3,
    num_history_responses=3,
    enable_user_memories=True,
    enable_session_summaries=True,
    read_chat_history=True,
    read_tool_call_history=True,
    enable_agentic_memory=True,
    debug_mode=True,
    instructions="""
        **Instructions for Answering Insurance Questions Using the Knowledge Base:**

        1. **Prioritize Knowledge Base Search:** Always attempt to answer the user's question by first searching the provided knowledge base.

        2. **Identify Key Information Needs & Keywords:** Understand what specific information the user is asking for. Extract the most relevant keywords and entities from their query (e.g., name, policy number, type of information).

        3. **Execute Knowledge Base Search:** Use the identified keywords to search the knowledge base. Be mindful of potential synonyms or related terms if the initial search is unsuccessful.

        4. **Analyze Search Results:** Carefully review the entries returned by the search. Identify the entry that directly addresses the user's question.

        5. **Extract and Formulate Answer:** Locate the specific data point needed to answer the user's query within the relevant knowledge base entry. Formulate a clear, concise, and grammatically correct answer using this information. Avoid directly copying the entire knowledge base entry.

        6. **Handle "No Match" Scenarios:** If your search yields no relevant results, inform the user politely that the information is not currently available in the knowledge base. For example: "I'm sorry, but I couldn't find that information in our current knowledge base."

        7. **Seek Clarification for Ambiguity:** If the user's question is unclear or ambiguous, ask for specific details before attempting to search the knowledge base. For example: "Could you please specify which [policy type/customer name/etc.] you are referring to?"

        8. **Maintain Professional Tone:** Always maintain a helpful and professional tone while providing information to the user.

        9. **Report Knowledge Base Issues:** If you identify any outdated, incorrect, or missing information in the knowledge base, flag it for review by the administrator.

        **Example Workflow:**

        * **User Question:** "What is John Smith's life insurance policy number?"
        * **Identify Keywords:** "John Smith", "life insurance", "policy number"
        * **Search Knowledge Base:** Search for entries containing these keywords.
        * **Relevant Entry Found:** (The John Smith entry we discussed earlier)
        * **Extract Answer:** Locate the value for the "policy\_number" field ("LIFE-001").
        * **Formulate Response:** "John Smith's life insurance policy number is LIFE-001."

        **Remember:** Your goal is to efficiently and accurately retrieve information from the knowledge base to answer user inquiries.
        """,
)

app = Flask(__name__)

@app.route('/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    user_input = data.get('user_input')
    if not user_input:
        return jsonify({"error": "Missing user_input"}), 400

    print(f"Received user input: '{user_input}'")

    try:
        response: RunResponse = agent.run(user_input)

        if response and hasattr(response, 'content'):
            agent_response_text = response.content
        else:
            agent_response_text = "No response content found."
            print(f"Warning: No 'content' attribute found in the RunResponse: {response}")

        return jsonify({"response": agent_response_text})

    except Exception as e:
        error_message = traceback.format_exc()
        print(f"Error in handle_query: {error_message}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

if __name__ == "__main__":
    # Comment out after first run if you hae loaded the knowledge base
    knowledge_base.load(recreate=False)

    app.run(debug=True, port=8000)