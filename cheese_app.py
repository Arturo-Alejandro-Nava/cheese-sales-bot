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


# --- 3. HIGH-VELOCITY DATA ENGINE ---
@st.cache_resource(ttl=1800) 
def build_instant_brain():
    # TCP Pooling for instant handshake (Speed)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    
    def scrape(url):
        try:
            # 1.0 second limit per page
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=1.0)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Kill bloat
            for trash in soup(["script", "style", "nav", "footer", "form", "svg"]):
                trash.decompose()
            
            # Smart cleaning that preserves numbers (Medal Counts)
            text = soup.get_text(separator=' ', strip=True)
            clean = re.sub(r'\s+', ' ', text)[:2500]
            return f"INFO [{url}]: {clean}\n"
        except: return ""

    # Live Website Scrape Target
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", # Contains Award history
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # Threaded Fetching
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape, urls))
        web_context = "".join(results)

    # Local PDF Load
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # SYSTEM PROMPT (The "Safety" Logic)
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    LIVE DATA: {web_context}
    
    STRICT RULES:
    1. **LANGUAGE**: If user speaks Spanish, Reply Spanish. If English, Reply English.
    2. **LINKS**: DO NOT generate PDF links. They break. 
       - If user asks for Catalog/Docs -> Link: "https://hcmakers.com/resources/"
       - If user asks for Video -> Link: "https://hcmakers.com/category-knowledge/"
    3. **MEDALS/AWARDS**: Check the text provided. Mention specific awards found (like American Cheese Society).
    4. **ACCURACY**: Use the PDF files I provided for numbers (Protein, Dimensions).
    5. **SPEED**: Answer directly. No fluff words.
    6. **NO IMAGES**.
    """
    return sys_instruction, pdfs


# --- 4. ENGINE INIT (Once per reboot) ---
with st.spinner("Ready..."):
    sys_prompt, ai_files = build_instant_brain()

# Temperature 0.0 forces the AI to choose the fastest logical answer
# candidate_count=1 prevents it from "considering alternatives"
config = genai.types.GenerationConfig(
    temperature=0.0, 
    candidate_count=1
)

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
            # Minimal spinner duration
            with st.spinner("Thinking..."):
                stream = model.generate_content(req_content, stream=True)
            
            # Pipe tokens to screen immediately
            def pipe():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(pipe)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.write("...")