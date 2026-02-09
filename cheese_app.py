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


# --- 1. BRAIN LOADING (Optimized for Adaptive Speed) ---
@st.cache_resource(ttl=3600) 
def setup_ai_resources():
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. Scrape critical context
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    web_context = ""
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(r.content, 'html.parser')
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:4000]
            web_context += f"SOURCE: {url} | CONTENT: {clean}\n"
        except: continue

    # 2. Upload PDFs (Heavy Lifting)
    pdfs = []
    local_files = glob.glob("*.pdf")
    for f in local_files:
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # 3. System Instruction (The Speed Controller)
    system_instruction = f"""
    You are the Senior Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    KNOWLEDGE BASE: {web_context}
    
    ADAPTIVE SPEED RULES:
    1. **BE DIRECT:** Do not use fluff like "That is a great question!" or "I can help with that." Just answer the question immediately.
    2. **LENGTH:** Answer briefly (1-3 sentences) for simple questions (Contact info, location, yes/no). Answer in detail ONLY if asked about Specs, Nutrition, or processes.
    3. **VIDEO:** If user mentions video/trends -> Link: https://hcmakers.com/category-knowledge/
    4. **DATA:** Use PDFs for hard numbers.
    5. **NO IMAGES:** Text only.
    """

    return system_instruction, pdfs

# --- INITIALIZATION ---
# Load resources once
with st.spinner("Initializing System..."):
    sys_prompt, ai_files = setup_ai_resources()

# Configure Model
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
        
        # Prepare content (PDFs + User Question)
        request_payload = ai_files + [prompt]
        
        try:
            # "Thinking" spinner appears immediately
            with st.spinner("Thinking..."):
                # Connect to stream
                stream = model.generate_content(request_payload, stream=True)
                
            # Direct Yield Function (Minimizes code lag)
            def fast_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            # Streamlit writes to screen instantly as data arrives
            response = st.write_stream(fast_stream)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Re-connecting...")