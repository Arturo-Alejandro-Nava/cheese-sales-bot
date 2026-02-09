import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re

# --- CONFIGURATION (UNIVERSAL) ---
# Works on Railway (Environment) & Streamlit Cloud (Secrets)
try:
    if "GOOGLE_API_KEY" in os.environ:
        API_KEY = os.environ["GOOGLE_API_KEY"]
    else:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Critical Error: No API Key found in Environment (Railway) or Secrets.")
    st.stop()

genai.configure(api_key=API_KEY)
# "gemini-1.5-flash" is currently the most reliable/fast production model
# We stick to Flash models for maximum speed
model = genai.GenerativeModel('gemini-2.0-flash')


# --- WEBPAGE CONFIG ---
st.set_page_config(page_title="Hispanic Cheese Makers", page_icon="🧀")


# --- HEADER (Styled to match your Brand) ---
# [1, 10, 1] Layout for nice centering
col1, col2, col3 = st.columns([1, 10, 1])

with col2:
    # 1. CENTERED LOGO
    # Nested columns to control logo size
    sub_col1, sub_col2, sub_col3 = st.columns([2, 1, 2])
    with sub_col2:
        possible_names = ["logo_new.png", "logo_new.jpg", "logo.jpg", "logo.png", "logo"]
        for p in possible_names:
            if os.path.exists(p):
                st.image(p, use_container_width=True)
                break
        else:
            st.write("🧀")

    # 2. TWO-LINE ELEGANT TITLE
    st.markdown(
        """
        <style>
        .header-text {
            font-family: 'Times New Roman', serif;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 3px;
            line-height: 1.5;
            color: #2c3e50;
            margin-top: 10px;
        }
        .line-one { font-size: 24px; font-weight: 300; }
        .line-two { font-size: 24px; font-weight: 400; }
        </style>
        <div class="header-text">
            <div class="line-one">Hispanic Cheese Makers</div>
            <div class="line-two">Nuestro Queso</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

st.markdown("---")


# --- 1. DATA LOADING (Optimized for Speed) ---
@st.cache_resource(ttl=3600) 
def load_all_data():
    # Use a Session for faster repeated connection reuse
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # A. Live Website Scrape
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/capabilities/",
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    web_text = ""
    
    for url in urls:
        try:
            r = session.get(url, headers=headers)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Extract text
            raw_text = soup.get_text(' ', strip=True)
            # REGEX OPTIMIZATION: Shrink extra whitespace to speed up AI reading
            clean_text = re.sub(r'\s+', ' ', raw_text)[:4000]
            web_text += f"\nSOURCE: {url}\nTEXT: {clean_text}\n"
        except: continue
        
    # B. Load Manual PDFs
    pdfs = []
    local_files = glob.glob("*.pdf")
    for f in local_files:
        try: pdfs.append(genai.upload_file(f))
        except: pass

    return web_text, pdfs


# --- INITIAL LOAD ---
# This runs once on startup
with st.spinner("Initializing System..."):
    live_web_text, ai_pdfs = load_all_data()


# --- CHAT ENGINE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# Display History
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- INPUT ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})


    with st.chat_message("assistant"):
        
        system_prompt = f"""
        You are the Senior Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
        
        RULES:
        1. **VIDEO/TREND REQUESTS**: IF the user asks to see a video, trends, or visual insights:
           - Reply EXACTLY: "You can watch our trend videos and category insights on our Knowledge Hub: https://hcmakers.com/category-knowledge/"
           - DO NOT provide other YouTube links. Send them to the Hub.
        
        2. **DATA/NUMBERS**: Use the provided PDF tables for specific numbers (Protein, Shelf Life, Pack Sizes).
        
        3. **CONTACT**: 
           - Plant: Kent, IL (752 N. Kent Road).
           - Phone: 847-258-0375.
        
        4. **NO IMAGES**: Text descriptions only.
        
        5. **LANG**: English or Spanish (Detect User Language).
        
        WEBSITE CONTEXT:
        {live_web_text}
        """
        
        payload = [system_prompt] + ai_pdfs + [prompt]
        
        # Display "Thinking..." then replace instantly with text
        try:
            with st.spinner("Thinking..."):
                # Connect to Google (High Speed Stream)
                stream = model.generate_content(payload, stream=True)
            
            # Helper to extract clean text chunks
            def clean_stream():
                for chunk in stream:
                    if chunk.text:
                        yield chunk.text

            # Stream response to screen
            response = st.write_stream(clean_stream)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        except:
            st.error("Just a moment, connection refreshing...")