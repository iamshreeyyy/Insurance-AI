# Streamlit app
def main():
    set_custom_css()
    
    st.title("💰 Financial Intelligence Assistant")
    st.markdown("""
    Welcome to your AI-powered financial research assistant! I can:
    - 📈 Analyze stock prices and financial metrics
    - 🔍 Research market trends and news
    - 💡 Provide investment recommendations
    """)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)
    
    # Get user input
    if prompt := st.chat_input("Ask your financial question..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Initialize agent team
        agent_team = initialize_insurance_agents()
        
        # Generate response
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""
            
            try:
                # Get the response from the agent
                response = agent_team.run(prompt)
                
                # Extract the content from the response
                if hasattr(response, 'content'):
                    response_content = response.content
                else:
                    response_content = str(response)
                
                # Simulate streaming effect
                for i in range(0, len(response_content), 5):
                    chunk = response_content[:i+5]
                    response_container.markdown(chunk + "▌", unsafe_allow_html=True)
                    time.sleep(0.02)  # Adjust speed here
                
                # Display final response
                response_container.markdown(response_content, unsafe_allow_html=True)
                full_response = response_content

            except Exception as e:
                full_response = f"⚠️ Error: {str(e)}"
                response_container.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()