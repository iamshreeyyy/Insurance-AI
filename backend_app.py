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
        collection="insurance_customers",
        uri=milvus_uri,
        embedder=openai_embedder
    ),
    chunking_strategy=DocumentChunking(),
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
    knowledge_base.load(recreate=True)

    app.run(debug=True, port=8000)