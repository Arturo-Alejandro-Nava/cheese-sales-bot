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


# --- 3. ULTRA-FAST DATA LOADER ---
@st.cache_resource(ttl=3600) 
def setup_brain_fast():
    def scrape_url(url):
        try:
            # 1 SECOND Timeout. If site lags, skip it to save speed.
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=1)
            soup = BeautifulSoup(r.content, 'html.parser')
            # 2000 char limit = Lighter Brain = Faster Response
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:2000]
            return f"[{url}]: {clean}\n"
        except: return ""

    # Essential Pages Only
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_url, urls))
        web_context = "".join(results)

    pdfs = []
    local_pdfs = glob.glob("*.pdf")
    for f in local_pdfs:
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # Lean Instructions
    sys_instruction = f"""
    Role: Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    Knowledge Base: {web_context}
    
    RULES:
    1. **LANGUAGE**: Input English -> Output English. Input Spanish -> Output Spanish.
    2. **VIDEO**: If topic is video/trends -> Link: https://hcmakers.com/category-knowledge/
    3. **MEDALS**: Say "Award-winning cheeses" (check website for details).
    4. **DATA**: Use PDFs for spec numbers.
    5. **NO IMAGES**.
    """

    return sys_instruction, pdfs

# --- 4. MODEL INIT (The Speed Hack) ---
with st.spinner("Connecting..."):
    sys_prompt, ai_files = setup_brain_fast()

# GenerationConfig with temperature=0.0 makes the AI stop "thinking" about creativity 
# and just select the most logical answer immediately.
speed_config = genai.types.GenerationConfig(
    temperature=0.0,
    max_output_tokens=300, # Keeps answers punchy
    candidate_count=1
)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt,
    generation_config=speed_config
)


# --- 5. CHAT ENGINE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- 6. ZERO-LATENCY RESPONSE ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        request_payload = ai_files + [prompt]
        
        try:
            # Spinner acts as instant visual feedback
            with st.spinner("Thinking..."):
                stream = model.generate_content(request_payload, stream=True)
            
            # Bare metal iterator (No logic slowing it down)
            def raw_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(raw_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Connection reset.")