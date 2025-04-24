import streamlit as st
import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

def query_agent(user_input: str):
    """Sends the user input to the backend agent API and returns the response.
    Handles potential errors and retries.
    """
    try:
        response = requests.post(f"{BACKEND_URL}/query", json={"user_input": user_input})
        response.raise_for_status()  # Raise HTTPError for bad status codes
        return response.json()["response"]
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error communicating with the backend: {http_err}")
        return f"Error: {http_err}"  # Return the error message
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"Connection error communicating with the backend: {conn_err}")
        return f"Error: {conn_err}"
    except requests.exceptions.Timeout as timeout_err:
        st.error(f"Timeout error communicating with the backend: {timeout_err}")
        return f"Error: {timeout_err}"
    except json.JSONDecodeError as json_err:
        st.error(f"Error decoding backend response: {json_err}")
        return "Error: Invalid response from the server."
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return f"Error: {e}"

def set_custom_css():
    """Applies custom CSS styles to the Streamlit app."""
    st.markdown("""
    <style>
        .main { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        .stTextInput input { border-radius: 20px; padding: 10px 15px; }
        .chat-message { padding: 1.5rem; border-radius: 15px; margin-bottom: 1rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .user-message { background: #ffffff; border: 1px solid #e0e0e0; }
        .bot-message { background: #007bff; color: white; }
        .stMarkdown table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
        .stMarkdown th { background-color: #007bff; color: white; padding: 12px; border: 1px solid #ddd; text-align: left; }
        .stMarkdown td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        .sidebar .stButton button { width: 100%; margin-bottom: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

def main():
    set_custom_css()

    st.sidebar.title("Insurance Chatbot Options")
    if st.sidebar.button("ℹ️ About"):
        st.sidebar.markdown("""
        This AI Assistant is designed to answer your insurance-related questions.
        """)
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.title("Insurance Chatbot")
    st.markdown("Ask your insurance-related questions.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Ask a question about insurance:"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response_content = ""
            # Simulate streaming -  Replace with actual agent logic
            agent_response = query_agent(prompt) # Get response from backend
            full_response_content = agent_response

            display_text = ""
            for i in range(0, len(full_response_content), 5):
                chunk = full_response_content[:i + 5]
                display_text = chunk
                response_container.markdown(display_text + "▌", unsafe_allow_html=True)
                time.sleep(0.01)

            response_container.markdown(full_response_content, unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": full_response_content})

if __name__ == "__main__":
    main()
