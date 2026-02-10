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


# --- 1. OPTIMIZED PARALLEL SCRAPER (Max Speed) ---
@st.cache_resource(ttl=3600) 
def setup_ai_resources():
    def fetch_url(url):
        try:
            # 2-second timeout for rapid failover
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Only text, no tags. Compress spaces. Max 3500 chars to save bandwidth.
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:3500]
            return f"DATA [{url}]: {clean}\n"
        except: return ""

    # Priority Pages
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", # Critical for awards/accuracy
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # Threaded Fetching
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_url, urls))
        web_context = "".join(results)

    # PDFs
    pdfs = []
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # Streamlined System Prompt
    system_instruction = f"""
    Role: Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    Context: {web_context}
    
    RULES:
    1. TRUTH CHECK: Use ONLY the provided Context and PDFs.
    2. ACCURACY: Do not hallucinate old award counts. If specific stats (like "21 medals") aren't in the text, refer generally to "Industry Awards" or the About Us page.
    3. MEDIA: For videos/trends -> https://hcmakers.com/category-knowledge/
    4. CONTACT: 752 N. Kent Road, Kent, IL | 847-258-0375.
    5. STYLE: Text only. No images. Fast, direct answers.
    """

    return system_instruction, pdfs

# --- INITIALIZATION ---
# Using spinner only on cold boot
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
            # Brief visual feedback
            with st.spinner("Thinking..."):
                # Stream start
                stream = model.generate_content(request_payload, stream=True)
                
            def turbo_stream():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(turbo_stream)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Re-connecting...")