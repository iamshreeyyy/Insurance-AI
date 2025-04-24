import streamlit as st
import requests
import json

BACKEND_URL = "http://localhost:8000"  # Ensure this matches your backend URL

def query_agent(user_input: str):
    """Sends the user input to the backend agent API and returns the response."""
    try:
        response = requests.post(f"{BACKEND_URL}/query", json={"user_input": user_input})
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        return f"Error communicating with the backend: {e}"
    except json.JSONDecodeError:
        return "Error decoding backend response."

st.title("Insurance Information Chatbot")

user_input = st.text_input("Ask a question about insurance:")

if user_input:
    with st.spinner("Thinking..."):
        agent_response = query_agent(user_input)
    st.write("Agent's Response:", agent_response)