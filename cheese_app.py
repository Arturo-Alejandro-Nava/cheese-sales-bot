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


# --- 3. HIGH-SPEED DATA ENGINE ---
@st.cache_resource(ttl=1800) 
def load_data_engine():
    # Session optimized for speed
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    
    def scrape_url(url):
        try:
            # STRICT 1-SECOND TIMEOUT. 
            # If the website hangs, we don't wait. We serve what we have.
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=1)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Destroy layout tags to save bandwidth
            for trash in soup(["script", "style", "nav", "footer", "form"]):
                trash.decompose()
                
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:3000]
            return f"INFO [{url}]: {clean}\n"
        except: return ""

    # Live Website Links
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # 1. Parallel Scrape
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_url, urls))
        web_context = "".join(results)

    # 2. Local PDF Load (This checks for new files on every restart/redeploy)
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # 3. Fast-Read System Prompt
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers (Nuestro Queso).
    
    CONTEXT FROM LIVE WEBSITE:
    {web_context}
    
    RULES:
    1. **LANGUAGE**: Answer in the same language as the user (English or Spanish).
    2. **VIDEO**: Send to Knowledge Hub: https://hcmakers.com/category-knowledge/
    3. **AWARDS**: Refer to "Industry Awards" (21+ medals) found in the text.
    4. **DATA**: Use PDFs for specific numbers.
    5. **NO IMAGES**.
    """
    return sys_instruction, pdfs


# --- 4. STARTUP ---
# Only shows spinner on the very first boot.
with st.spinner("Connecting..."):
    sys_prompt, ai_files = load_data_engine()

# Speed Config: Temp 0 = No creativity = Faster calculation
speed_config = genai.types.GenerationConfig(
    temperature=0.0,
    candidate_count=1,
    max_output_tokens=500
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


# --- 6. INSTANT RESPONSE UI ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        request_payload = ai_files + [prompt]
        
        try:
            # NOTE: We removed the visual spinner to make it feel snappier.
            # The text will simply start appearing the moment it is ready.
            
            stream = model.generate_content(request_payload, stream=True)
            
            def pipe_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            # write_stream manages the typing effect
            response = st.write_stream(pipe_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.write("...")