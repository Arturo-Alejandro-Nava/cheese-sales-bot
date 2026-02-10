import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re
import concurrent.futures

# --- CONFIGURATION (UNIVERSAL) ---
try:
    if "GOOGLE_API_KEY" in os.environ:
        API_KEY = os.environ["GOOGLE_API_KEY"]
    else:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Critical Error: No API Key found.")
    st.stop()

genai.configure(api_key=API_KEY)


# --- WEBPAGE CONFIG ---
st.set_page_config(page_title="Hispanic Cheese Makers", page_icon="🧀")


# --- HEADER ---
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


# --- 1. HYPER-THREADED DATA LOADER (Fastest Possible) ---
@st.cache_resource(ttl=3600) 
def setup_ai_resources():
    # Helper to scrape one URL
    def fetch_url(url):
        try:
            # Short timeout, fast User Agent
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Only keep the most valuable text (P, DIV, H1-H6)
            text_blobs = [t.get_text() for t in soup.find_all(['p', 'h1', 'h2', 'h3', 'div'])]
            raw = " ".join(text_blobs)
            clean = re.sub(r'\s+', ' ', raw)[:4500]
            return f"SOURCE: {url} | DATA: {clean}\n"
        except: return ""

    # Target Pages
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", # Award Info here
        "https://hcmakers.com/quality/",   
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    web_context = ""
    # Parallel Processing: Fetch all URLs at the EXACT same time
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_url, urls))
        web_context = "".join(results)

    # Load PDFs
    pdfs = []
    local_files = glob.glob("*.pdf")
    for f in local_files:
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # Precise System Instructions
    system_instruction = f"""
    You are the Senior Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    KNOWLEDGE BASE: {web_context}
    
    CRITICAL INSTRUCTIONS:
    1. **ACCURACY CHECK**: You must ONLY use the KNOWLEDGE BASE text above and attached PDFs. 
    2. **AWARDS/MEDALS**: Do not use your own training data about medal counts. If the exact number isn't in the text, say: "We are an award-winning cheese manufacturer," and refer to the website.
    3. **VIDEO**: Link to: https://hcmakers.com/category-knowledge/ if asked.
    4. **CONTACT**: Plant: Kent, IL (752 N. Kent Road). Phone: 847-258-0375.
    5. **NO IMAGES**: Text only.
    """

    return system_instruction, pdfs

# --- INITIALIZATION ---
# Using spinner only on first boot
with st.spinner("Initializing System..."):
    sys_prompt, ai_files = setup_ai_resources()

# Load Model
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt
)


# --- CHAT ENGINE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --- DISPLAY HISTORY ---
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- INPUT & RESPONSE ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})


    with st.chat_message("assistant"):
        request_payload = ai_files + [prompt]
        
        try:
            # Spinner visible while connecting, vanishes instantly on first token
            with st.spinner("Thinking..."):
                stream = model.generate_content(request_payload, stream=True)
                
            def lightning_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(lightning_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Connection refreshing...")