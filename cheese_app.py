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


# --- 2. VISUAL HEADER ---
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


# --- 3. PARALLEL DATA LOADER (THE SPEED ENGINE) ---
# TTL=1800 means it updates from the live website every 30 minutes
@st.cache_resource(ttl=1800) 
def build_live_brain():
    
    # 1. SCRAPER FUNCTION (Stripped for speed)
    def fetch_data(url):
        try:
            # 2 second timeout - if a page lags, drop it to save speed
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Extract text -> Remove tabs/newlines -> Limit to 3000 chars
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:3000]
            return f"SOURCE: {url} | DATA: {clean}\n"
        except: return ""

    # 2. TARGET LIST
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/capabilities/",
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/about-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # 3. PARALLEL EXECUTION (This runs all URLs simultaneously)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_data, urls))
        web_knowledge = "".join(results)

    # 4. LOAD PDFS (These update whenever you push to GitHub)
    pdfs = []
    local_files = glob.glob("*.pdf")
    for f in local_files:
        try: pdfs.append(genai.upload_file(f))
        except: pass

    # 5. PRE-COMPILED SYSTEM INSTRUCTIONS
    # We bake the rules in here to save processing time later
    sys_instruction = f"""
    You are the Senior Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    
    LIVE WEBSITE DATA:
    {web_knowledge}
    
    RULES:
    1. **VIDEO LINKS**: If asked about video/trends, Reply: "View our Knowledge Hub videos: https://hcmakers.com/category-knowledge/"
    2. **CONTACT**: Plant: 752 N. Kent Road, Kent, IL. Phone: 847-258-0375.
    3. **DATA**: Use the PDFs attached for spec numbers.
    4. **NO IMAGES**: Text only.
    5. **LANGUAGE**: Detect input language (En/Es) and reply in same language.
    """
    
    return sys_instruction, pdfs


# --- 4. STARTUP (Runs Once) ---
# Visual feedback only happens on first load
with st.spinner("Connecting to Live Data..."):
    sys_prompt, ai_files = build_live_brain()

# Load the "Flash" Model (Fastest)
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


# --- 6. INSTANT RESPONSE LOOP ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})


    with st.chat_message("assistant"):
        
        # Prepare content (Only variable data is the question now)
        request_content = ai_files + [prompt]
        
        try:
            # Shortest possible "Thinking" time
            with st.spinner("Thinking..."):
                stream = model.generate_content(request_content, stream=True)
            
            # Direct yield to screen
            def lightning_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(lightning_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Connection reset.")