import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re
import concurrent.futures

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Hispanic Cheese Makers", page_icon="🧀")

try:
    if "GOOGLE_API_KEY" in os.environ:
        API_KEY = os.environ["GOOGLE_API_KEY"]
    else:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Critical Error: No API Key found.")
    st.stop()

genai.configure(api_key=API_KEY)


# --- 2. HEADER ---
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


# --- 3. SONIC-SPEED DATA ENGINE ---
@st.cache_resource(ttl=1800) 
def load_data_engine():
    # TCP Pooling for instant handshake
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5)
    session.mount('https://', adapter)
    
    def scrape_micro(url):
        try:
            # 0.8s TIMEOUT: If it lags, we leave.
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.8)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Kill bloat
            for x in soup(["script", "style", "nav", "footer", "form", "svg"]):
                x.decompose()
                
            # Limit to 1500 chars (Top-Level Data Only) for maximum CPU speed
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:1500]
            return f"[{url}]: {clean}\n"
        except: return ""

    # Live Website
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # Run all simultaneously
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_micro, urls))
        web_context = "".join(results)

    # Local PDF Files
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # "Caveman" Instructions: Fewer words = Faster AI processing
    sys_instruction = f"""
    Role: Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    Data: {web_context}
    
    FAST RULES:
    1. MATCH USER LANG (Esp/Eng).
    2. BE DIRECT.
    3. VIDEOS: https://hcmakers.com/category-knowledge/
    4. MEDALS: Mention "Multiple Industry Awards".
    5. SPECS: Use PDFs.
    6. TEXT ONLY.
    """
    return sys_instruction, pdfs


# --- 4. ENGINE INIT ---
with st.spinner("Loading..."):
    sys_prompt, ai_files = load_data_engine()

# Speed Config
config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt,
    generation_config=config
)


# --- 5. CHAT UI ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- 6. INSTANT INTERACTION ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        req = ai_files + [prompt]
        
        try:
            # SPINNER: Only exists for the tiny network gap.
            with st.spinner("Thinking..."):
                stream = model.generate_content(req, stream=True)
            
            # YIELD: Instantly passes letters to screen.
            def fast_yield():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(fast_yield)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("...")