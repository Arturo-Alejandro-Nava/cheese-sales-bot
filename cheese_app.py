import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re
import concurrent.futures

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


# --- 1. OPTIMIZED BRAIN (Parallel + Strict Lang) ---
@st.cache_resource(ttl=3600) 
def setup_ai_resources():
    # 1. Scraping Function (Fastest Possible)
    def fetch_url(url):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Compress white space and limit char count for speed
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:3500]
            return f"[{url}]: {clean}\n"
        except: return ""

    # Target Pages
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # 2. Parallel Fetch (5x Faster than standard)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_url, urls))
        web_context = "".join(results)

    # 3. Load PDFs
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # 4. STRICT SYSTEM PROMPT
    # We moved Language Rules to the TOP so the AI obeys them first.
    system_instruction = f"""
    You are the Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    
    *** CRITICAL LANGUAGE RULES ***
    1. IF INPUT IS SPANISH -> RESPONSE MUST BE SPANISH.
    2. IF INPUT IS ENGLISH -> RESPONSE MUST BE ENGLISH.
    3. Do not mix languages. Match the user's language exactly.
    
    KNOWLEDGE BASE: 
    {web_context}
    
    OPERATIONAL RULES:
    1. TRUTH CHECK: Use ONLY the provided Knowledge Base and PDFs.
    2. ACCURACY: Do not hallucinate. If you don't know the exact number of medals, say "We have won numerous industry awards" and refer to the website.
    3. MEDIA: For videos/trends -> https://hcmakers.com/category-knowledge/
    4. CONTACT: 752 N. Kent Road, Kent, IL | 847-258-0375.
    5. NO IMAGES.
    """

    return system_instruction, pdfs

# --- INITIALIZATION ---
# Spinner only shows on cold boot/redeploy
with st.spinner("System initializing..."):
    sys_prompt, ai_files = setup_ai_resources()

# Load Model
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt
)


# --- CHAT ENGINE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

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
            # Spinner acts as visual confirmation, vanishes instantly
            with st.spinner("..."):
                stream = model.generate_content(request_payload, stream=True)
            
            def turbo_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(turbo_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Connection hiccup...")