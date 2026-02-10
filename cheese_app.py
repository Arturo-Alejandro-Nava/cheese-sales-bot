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


# --- 3. HIGH-SPEED DATA LOADER ---
@st.cache_resource(ttl=3600) 
def setup_brain_fast():
    def scrape_url(url):
        try:
            # 1.5s timeout for ultra-fast scraping
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=1.5)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Strips ALL fluff. Limits to 2500 chars per page to boost speed.
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:2500]
            return f"[{url}]: {clean}\n"
        except: return ""

    # Targeted Pages (Only the ones that matter)
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # Parallel Processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_url, urls))
        web_context = "".join(results)

    # PDF Loading
    pdfs = []
    local_pdfs = glob.glob("*.pdf")
    for f in local_pdfs:
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # Minimalist System Prompt (Smaller = Faster)
    sys_instruction = f"""
    Role: Senior Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    Knowledge Base: {web_context}
    
    FAST RULES:
    1. IF SPANISH -> SPANISH. IF ENGLISH -> ENGLISH.
    2. BE DIRECT. Skip polite filler ("Hello! That is a great question"). Just answer.
    3. VIDEOS -> https://hcmakers.com/category-knowledge/
    4. DATA -> Use PDFs for specs.
    5. CONTACT -> 752 N. Kent Road, Kent, IL | 847-258-0375.
    6. MEDALS -> Refer to "Numerous Industry Awards" unless exact count is known.
    7. NO IMAGES.
    """

    return sys_instruction, pdfs

# --- 4. MODEL INITIALIZATION ---
# Loading only happens ONCE.
with st.spinner("Connecting..."):
    sys_prompt, ai_files = setup_brain_fast()

# Initialize Flash Model
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt
)


# --- 5. CHAT ENGINE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- 6. FAST INPUT & RESPONSE ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        request_payload = ai_files + [prompt]
        
        try:
            # "Thinking" shows for milliseconds
            with st.spinner("Thinking..."):
                stream = model.generate_content(request_payload, stream=True)
            
            # Instant Token Yielder
            def hyper_speed_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            # Streamlit types immediately
            response = st.write_stream(hyper_speed_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Reconnect...")