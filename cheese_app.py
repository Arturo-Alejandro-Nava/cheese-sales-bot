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


# --- 3. FEATHERWEIGHT DATA ENGINE (Max Speed) ---
@st.cache_resource(ttl=1800) 
def load_feather_brain():
    # Keep connection open for speed
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    
    def scrape_light(url):
        try:
            # 0.8s Timeout: Fast or nothing.
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.8)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Massive De-bloating: Removing all these tags makes the payload tiny
            for trash in soup(["script", "style", "nav", "footer", "form", "svg", "noscript", "iframe"]):
                trash.decompose()
            
            # Keep only the essential text (Limit 1500 chars)
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
    
    # Run in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_light, urls))
        web_context = "".join(results)

    # Local PDFs
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # Optimized System Instructions
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    LIVE DATA: {web_context}
    
    RULES:
    1. **LANGUAGE**: Answer in the user's language (Spanish/English).
    2. **LINKS**: Doc Link -> https://hcmakers.com/resources/ | Video Link -> https://hcmakers.com/category-knowledge/
    3. **AWARDS**: Reference specific awards if found in text (e.g. 21 medals).
    4. **ACCURACY**: Use PDFs for specific specs.
    5. **NO IMAGES**.
    """
    return sys_instruction, pdfs


# --- 4. STARTUP ---
with st.spinner("Connecting..."):
    sys_prompt, ai_files = load_feather_brain()

# Fast Config
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


# --- 6. INSTANT INPUT WITH "THINKING" INDICATOR ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        req_content = ai_files + [prompt]
        
        try:
            # "Thinking" appears instantly, then VANISHES the millisecond text arrives.
            with st.spinner("Thinking..."):
                stream = model.generate_content(req_content, stream=True)
            
            def instant_yield():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            # Streamlit types the response
            response = st.write_stream(instant_yield)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("...")