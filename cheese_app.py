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


# --- 2. UI HEADER (Lightweight) ---
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


# --- 3. HIGH-VELOCITY DATA ENGINE ---
# Updates from website every 30 minutes (TTL 1800)
@st.cache_resource(ttl=1800) 
def load_hyper_brain():
    
    # Session Object for Connection Pooling (Speed Trick)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5)
    session.mount('https://', adapter)
    
    def scrape_lean(url):
        try:
            # 1.5s timeout: Speed is priority.
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=1.5)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # AGGRESSIVE CLEANING: Remove menus, scripts, styles to reduce token load
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            # Limit to 2000 chars per page to force speed
            text = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:2000]
            return f"[{url}]: {text}\n"
        except: return ""

    # Priority Pages
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", # Award Info
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # Multi-Threaded Scraping
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_lean, urls))
        web_context = "".join(results)

    # PDF Loader (From GitHub)
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
        
    # Micro-Instructions (Fewer words for AI to process)
    sys_instruction = f"""
    Role: Senior Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    Knowledge: {web_context}
    
    SPEED RULES:
    1. INPUT LANGUAGE = OUTPUT LANGUAGE.
    2. BE DIRECT. Answer immediately. No fluff.
    3. VIDEOS: Link -> https://hcmakers.com/category-knowledge/
    4. MEDALS: Mention "Multiple Industry Awards" if exact count unknown.
    5. DATA: Use attached PDFs.
    6. TEXT ONLY.
    """
    
    return sys_instruction, pdfs


# --- 4. ENGINE START ---
# Initial load
with st.spinner("Connecting..."):
    sys_prompt, ai_files = load_hyper_brain()

# SPEED CONFIGURATION: Temperature 0.0 forces "Greedy Decoding" (Fastest math)
fast_config = genai.types.GenerationConfig(
    temperature=0.0,
    candidate_count=1,
    max_output_tokens=500
)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt,
    generation_config=fast_config
)


# --- 5. UI & CHAT ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- 6. ZERO-LAG RESPONSE LOOP ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})


    with st.chat_message("assistant"):
        request_payload = ai_files + [prompt]
        
        try:
            # Thinking text appears instantly
            with st.spinner("Thinking..."):
                stream = model.generate_content(request_payload, stream=True)
                
            # Direct Pipe: Yield text to screen the millisecond it arrives
            def raw_pipe():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(raw_pipe)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Reloading...")