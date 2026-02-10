import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re

# --- CONFIGURATION (UNIVERSAL) ---
try:
    if "GOOGLE_API_KEY" in os.environ:
        API_KEY = os.environ["GOOGLE_API_KEY"]
    else:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Critical Error: No API Key found.")
    st.stop()

genai.configure(api_key=API_KEY)


# --- WEBPAGE CONFIG ---
st.set_page_config(page_title="Hispanic Cheese Makers", page_icon="🧀")


# --- HEADER ---
col1, col2, col3 = st.columns([1, 10, 1])
with col2:
    sub_col1, sub_col2, sub_col3 = st.columns([2, 1, 2])
    with sub_col2:
        possible_names = ["logo_new.png", "logo_new.jpg", "logo.jpg", "logo.png", "logo"]
        for p in possible_names:
            if os.path.exists(p):
                st.image(p, use_container_width=True)
                break
        else:
            st.write("🧀")

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


# --- 1. BRAIN LOADING (Accuracy Focus) ---
@st.cache_resource(ttl=3600) 
def setup_ai_resources():
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. Expanded URL list to ensure we catch the Award Count
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", # Contains Medal Info
        "https://hcmakers.com/quality/",   # Contains Certifications
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    web_context = ""
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(r.content, 'html.parser')
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:5000]
            web_context += f"SOURCE: {url} | CONTENT: {clean}\n"
        except: continue

    # 2. Upload PDFs (Heavy Lifting)
    pdfs = []
    local_files = glob.glob("*.pdf")
    for f in local_files:
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # 3. System Instruction (Strict Grounding)
    system_instruction = f"""
    You are the Senior Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    KNOWLEDGE BASE: {web_context}
    
    CRITICAL RULES (GROUNDING):
    1. **SOURCE OF TRUTH:** You must ONLY answer using the 'KNOWLEDGE BASE' text above and the provided PDFs. 
    2. **NO HALLUCINATIONS:** Do not use outside training data (like old award counts). If the specific number (e.g., medal count) is not in the text below, simply say "We have won numerous industry awards" and direct them to the About Us page.
    
    STANDARD RULES:
    1. **CONTACT**: Plant: Kent, IL (752 N. Kent Road). Phone: 847-258-0375.
    2. **VIDEO**: Link to https://hcmakers.com/category-knowledge/
    3. **FORMAT**: Text only (No images). Be concise and professional.
    """

    return system_instruction, pdfs

# --- INITIALIZATION ---
with st.spinner("Initializing System..."):
    sys_prompt, ai_files = setup_ai_resources()

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt
)


# --- CHAT ENGINE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --- DISPLAY HISTORY ---
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- INPUT & RESPONSE ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})


    with st.chat_message("assistant"):
        request_payload = ai_files + [prompt]
        
        try:
            with st.spinner("Thinking..."):
                stream = model.generate_content(request_payload, stream=True)
                
            def accurate_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(accurate_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Re-connecting...")