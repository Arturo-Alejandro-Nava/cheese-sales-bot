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


# --- 3. FEATHERWEIGHT DATA ENGINE ---
@st.cache_resource(ttl=1800) 
def load_feather_brain():
    # TCP Connection Pooling
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    
    def scrape_light(url):
        try:
            # 0.8s Timeout (Zero Tolerance for Lag)
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.8)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Massive De-bloating
            # Removes all interactive elements to focus purely on text data
            for x in soup(["script", "style", "nav", "footer", "form", "svg", "noscript", "iframe"]):
                x.decompose()
            
            # Reduce context window to 1500 chars to increase processing speed
            text = soup.get_text(separator=' ', strip=True)
            clean = re.sub(r'\s+', ' ', text)[:1500]
            return f"INFO [{url}]: {clean}\n"
        except: return ""

    # Scrape Targets
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_light, urls))
        web_context = "".join(results)

    # PDFs
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # Minimalist Instruction Set (Processing speed optimized)
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    LIVE DATA: {web_context}
    
    RULES:
    1. **LANGUAGE**: Output in same language as input.
    2. **LINKS**: No broken links. For docs -> https://hcmakers.com/resources/. For Videos -> https://hcmakers.com/category-knowledge/
    3. **MEDALS**: Reference "21+ Awards" / "Industry Gold Medals".
    4. **SPEED**: Answer directly.
    5. **NO IMAGES**.
    """
    return sys_instruction, pdfs


# --- 4. STARTUP ---
# Only happens once on deploy
with st.spinner("Connected."):
    sys_prompt, ai_files = load_feather_brain()

# Greedy Configuration (Temperature 0)
config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt,
    generation_config=config
)


# --- 5. UI ---
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
            # NO visual spinner anymore. Text starts arriving immediately.
            stream = model.generate_content(req_content, stream=True)
            
            def immediate_yield():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(immediate_yield)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("...")