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


# --- 3. ZERO-LAG DATA ENGINE ---
@st.cache_resource(ttl=1800) 
def build_brain():
    # Use Session to keep TCP connection alive (Speed Hack)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5)
    session.mount('https://', adapter)
    
    def scrape(url):
        try:
            # 1.0 second timeout. Speed is king.
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=1.0)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Kill slow/heavy tags immediately
            for trash in soup(["script", "style", "nav", "footer", "iframe"]):
                trash.decompose()
            
            # Extract raw text & minify whitespace
            text = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:2500]
            return f"INFO [{url}]: {text}\n"
        except: return ""

    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # Execute scrapes in parallel (simultaneous)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape, urls))
        web_context = "".join(results)

    # Local PDFs
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # Instruction optimized for short/fast output generation
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    LIVE DATA: {web_context}
    
    FAST RESPONSE RULES:
    1. MATCH USER LANGUAGE (English/Spanish).
    2. BE CONCISE (Avoid long paragraphs, answer directly).
    3. VIDEOS: Link -> https://hcmakers.com/category-knowledge/
    4. MEDALS: 21+ Medals/Awards (American Cheese Society Gold).
    5. DATA: Use PDF tables.
    6. TEXT ONLY.
    """
    return sys_instruction, pdfs


# --- 4. STARTUP ---
# Only loads once
with st.spinner("Connecting..."):
    sys_prompt, ai_files = build_brain()

# Temperature 0.0 = Math over Creativity = Faster
config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt,
    generation_config=config
)


# --- 5. CHAT ENGINE ---
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
        req_content = ai_files + [prompt]
        
        try:
            # SPINNER: Only exists while the signal travels. Vanishes immediately on first byte.
            with st.spinner("Thinking..."):
                stream = model.generate_content(req_content, stream=True)
            
            # PURE PIPE: Delivers tokens to screen immediately without buffer
            def rapid_yield():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(rapid_yield)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("...")