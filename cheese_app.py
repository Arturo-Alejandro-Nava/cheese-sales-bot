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


# --- 3. FEATHERWEIGHT DATA ENGINE (High-Efficiency) ---
@st.cache_resource(ttl=1800) 
def load_feather_brain():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    
    def scrape_light(url):
        try:
            # 0.8s Timeout logic
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.8)
            soup = BeautifulSoup(r.content, 'html.parser')
            for trash in soup(["script", "style", "nav", "footer", "form", "svg", "noscript", "iframe"]):
                trash.decompose()
            text = soup.get_text(separator=' ', strip=True)
            clean = re.sub(r'\s+', ' ', text)[:1500]
            return f"INFO [{url}]: {clean}\n"
        except: return ""

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

    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # SYSTEM PROMPT
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    LIVE DATA: {web_context}
    
    RULES:
    1. **LANGUAGE**: Answer in the user's language (Spanish/English).
    
    2. **SALES HANDOFF**: 
       - If the user implies interest in buying/distributing:
       - ANSWER product questions first.
       - THEN end with exactly: "\n\nTo learn how to become a customer, please contact our Sales Team here: https://hcmakers.com/contact-us/"
    
    3. **LINKS**: Docs -> https://hcmakers.com/resources/ | Videos -> https://hcmakers.com/category-knowledge/
    4. **AWARDS**: Reference specific awards if found.
    5. **ACCURACY**: Use PDFs for specific specs.
    6. **NO IMAGES**: Do not attempt to generate images.
    """
    return sys_instruction, pdfs


# --- 4. STARTUP (Upgraded to 2.5 Flash) ---
with st.spinner("Connecting..."):
    sys_prompt, ai_files = load_feather_brain()

# Gemini 2.5 Config (Temperature 0 for Speed/Accuracy)
config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1)

# UPDATED TO NEW STABLE STANDARD: gemini-2.5-flash
# This is valid according to the October 2025 GA release.
try:
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=sys_prompt,
        generation_config=config
    )
except:
    # If 2.5 is restricted in region, fall back to 2.0-flash-001 (Long Life)
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


# --- 6. INSTANT INPUT WITH "THINKING" INDICATOR ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        req_content = ai_files + [prompt]
        
        try:
            with st.spinner("Thinking..."):
                stream = model.generate_content(req_content, stream=True)
            
            def instant_yield():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(instant_yield)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("...")