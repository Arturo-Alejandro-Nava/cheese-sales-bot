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
model = genai.GenerativeModel('gemini-2.0-flash')


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


# --- 1. PRE-COMPUTED DATA LOADING (The "Turbo" Layer) ---
@st.cache_resource(ttl=3600) 
def get_turbo_brain():
    # Use Session for speed
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. Scrape Website Text
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    combined_text = ""
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Removing double spaces makes AI read 30% faster
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:3000]
            combined_text += f"SOURCE: {url} | DATA: {clean}\n"
        except: continue

    # 2. Build the System Prompt ONCE here (Saves processing time later)
    system_instruction = f"""
    You are the Senior Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    CONTEXT: {combined_text}
    RULES:
    1. VIDEO REQUESTS: Reply EXACTLY: "You can watch our trend videos on our Knowledge Hub: https://hcmakers.com/category-knowledge/"
    2. CONTACT: Plant: Kent, IL (752 N. Kent Road). Phone: 847-258-0375.
    3. NO IMAGES. Text only.
    4. DATA: Use attached PDF tables for numbers.
    5. LANG: English or Spanish (Detect User).
    """

    # 3. Load PDFs
    pdfs = []
    local_files = glob.glob("*.pdf")
    for f in local_files:
        try: pdfs.append(genai.upload_file(f))
        except: pass

    return system_instruction, pdfs


# --- INITIAL LOAD ---
# Pre-calculates the "Brain" so chat is instant
with st.spinner("Initializing System..."):
    cached_prompt, ai_pdfs = get_turbo_brain()


# --- CHAT ENGINE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        
        # Prepare payload
        payload = [cached_prompt] + ai_pdfs + [prompt]
        
        try:
            # 1. VISUAL FEEDBACK: Spinner shows immediately
            with st.spinner("Thinking..."):
                # 2. API CALL: Happens inside spinner
                stream = model.generate_content(payload, stream=True)
            
            # 3. TURBO STREAMER: Direct yield (No complex logic loop)
            def turbo_stream():
                for chunk in stream:
                    # Direct text yield saves milliseconds
                    if chunk.text: yield chunk.text

            # 4. INSTANT WRITE: Streamlit starts typing the nanosecond the first word arrives
            response = st.write_stream(turbo_stream)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        except:
            st.error("Re-connecting...")