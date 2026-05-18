"""
Streamlit UI for Financial Insights Copilot - Graph RAG
Professional interface with LLM-powered answers
"""

import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime

st.set_page_config(
    page_title="Financial Insights Copilot",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'current_ticker' not in st.session_state:
    st.session_state['current_ticker'] = 'GOOGL'
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'api_url' not in st.session_state:
    st.session_state['api_url'] = 'http://localhost:8000'

AVAILABLE_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA']
COMPANY_NAMES = {
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'TSLA': 'Tesla Inc.',
    'NVDA': 'NVIDIA Corporation'
}

NAME_TO_TICKER = {
    'apple': 'AAPL', 'Apple': 'AAPL', 'AAPL': 'AAPL',
    'microsoft': 'MSFT', 'Microsoft': 'MSFT', 'MSFT': 'MSFT',
    'google': 'GOOGL', 'Google': 'GOOGL', 'GOOGL': 'GOOGL', 'alphabet': 'GOOGL',
    'amazon': 'AMZN', 'Amazon': 'AMZN', 'AMZN': 'AMZN',
    'tesla': 'TSLA', 'Tesla': 'TSLA', 'TSLA': 'TSLA',
    'nvidia': 'NVDA', 'Nvidia': 'NVDA', 'NVIDIA': 'NVDA', 'NVDA': 'NVDA'
}


def extract_ticker_from_question(question: str):
    question_lower = question.lower()
    for name, ticker in NAME_TO_TICKER.items():
        if name.lower() in question_lower:
            cleaned = re.sub(re.escape(name), '', question, flags=re.IGNORECASE).strip()
            return cleaned, ticker
    return question, None


def check_backend_health():
    try:
        response = requests.get(f"{st.session_state['api_url']}/health", timeout=3)
        return response.status_code == 200
    except:
        return False


def ask_question(question: str, ticker: str = None):
    try:
        payload = {"question": question}
        if ticker:
            payload["ticker"] = ticker
        response = requests.post(
            f"{st.session_state['api_url']}/api/ask",
            json=payload,
            timeout=90
        )
        if response.status_code == 200:
            return response.json()
        return {"error": f"API Error: {response.status_code}", "answer": "Could not process request."}
    except Exception as e:
        return {"error": str(e), "answer": f"Error: {str(e)}"}


def analyze_impact(ticker: str, issue: str):
    try:
        response = requests.post(
            f"{st.session_state['api_url']}/api/impact",
            json={"ticker": ticker, "issue": issue},
            timeout=90
        )
        if response.status_code == 200:
            return response.json()
        return {"error": f"API Error: {response.status_code}", "analysis": "Analysis failed"}
    except Exception as e:
        return {"error": str(e), "analysis": f"Error: {str(e)}"}


def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Financial Insights Copilot")
        st.markdown("Graph RAG powered financial analysis system")
        st.markdown("---")
        
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.button("Login", use_container_width=True):
            if email and password:
                st.session_state['authenticated'] = True
                st.session_state['user_email'] = email
                st.rerun()
            else:
                st.warning("Please enter both email and password")


def show_dashboard():
    with st.sidebar:
        st.markdown(f"Welcome, {st.session_state.get('user_email', 'User')}")
        st.markdown("---")
        
        if check_backend_health():
            st.success("Backend Connected")
        else:
            st.error("Backend Offline")
            st.info("Start backend: uvicorn api:app --reload --port 8000")
        
        st.markdown("---")
        
        current_ticker = st.selectbox(
            "Default Company",
            AVAILABLE_TICKERS,
            format_func=lambda x: f"{x} - {COMPANY_NAMES.get(x, x)}",
            index=AVAILABLE_TICKERS.index(st.session_state.get('current_ticker', 'GOOGL'))
        )
        st.session_state['current_ticker'] = current_ticker
        
        st.markdown("---")
        st.caption("Powered by Neo4j, Weaviate, and Groq LLM")
        
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.title("Financial Insights Copilot")
    st.markdown("---")
    
    st.header("Ask Questions")
    
    if st.button("Clear Chat History", use_container_width=False):
        st.session_state['chat_history'] = []
        st.rerun()
    
    st.markdown("---")
    
    for msg in st.session_state.get('chat_history', [])[-20:]:
        if msg['role'] == 'user':
            st.markdown(f"**You:** {msg['content']}")
        else:
            st.markdown(f"**Assistant:** {msg['content']}")
        st.markdown("---")
    
    with st.expander("Example Questions", expanded=False):
        st.markdown("""
        - What is Tesla's total assets for 2025?
        - How has Apple's revenue changed over time?
        - Show me Microsoft's net income trend
        - impact TSLA | supply chain disruption in China
        - impact GOOGL | antitrust investigation by EU
        - Any recent news about NVIDIA?
        """)
    
    question = st.text_area(
        "Your Question",
        placeholder="Example: What is Tesla's total assets for 2025?",
        height=100
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        ask_button = st.button("Get Answer", use_container_width=True)
    with col2:
        use_default_ticker = st.checkbox("Use default company", value=False)
    
    if ask_button and question:
        with st.spinner("Analyzing with Graph RAG..."):
            cleaned_question, detected_ticker = extract_ticker_from_question(question)
            
            if use_default_ticker:
                ticker_to_use = current_ticker
                st.info(f"Using: {ticker_to_use} - {COMPANY_NAMES.get(ticker_to_use, ticker_to_use)}")
            elif detected_ticker:
                ticker_to_use = detected_ticker
                st.info(f"Detected: {ticker_to_use} - {COMPANY_NAMES.get(ticker_to_use, ticker_to_use)}")
            else:
                ticker_to_use = current_ticker
            
            if question.lower().strip().startswith('impact'):
                parts = question[7:].split('|')
                if len(parts) >= 2:
                    impact_ticker = parts[0].strip().upper()
                    issue = parts[1].strip()
                    result = analyze_impact(impact_ticker, issue)
                    if 'error' not in result:
                        answer = result.get('analysis', 'No analysis available')
                    else:
                        answer = result.get('error', 'Analysis failed')
                else:
                    answer = "Please use format: impact TSLA | supply chain disruption"
            else:
                result = ask_question(cleaned_question, ticker_to_use)
                if 'error' not in result:
                    answer = result.get('answer', 'No answer available')
                else:
                    answer = result.get('error', 'Unknown error')
            
            st.session_state['chat_history'].append({'role': 'user', 'content': question})
            st.session_state['chat_history'].append({'role': 'assistant', 'content': answer})
            st.rerun()
    
    elif ask_button and not question:
        st.warning("Please enter a question")


def main():
    if not st.session_state.get('authenticated', False):
        show_login_page()
    else:
        show_dashboard()


if __name__ == "__main__":
    main()