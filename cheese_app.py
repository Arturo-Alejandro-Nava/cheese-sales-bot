import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re
import concurrent.futures

# --- 1. CONFIGURATION (Must be first) ---
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


# --- 3. THE "INSTANT BRAIN" (Cached & Threaded) ---
@st.cache_resource(ttl=3600) 
def load_and_prepare_brain():
    # Helper for fast parallel scraping
    def scrape_url(url):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
            soup = BeautifulSoup(r.content, 'html.parser')
            # Strips heavy code, keeps only words, compresses whitespace
            clean_text = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:4000]
            return f"SOURCE: {url} | DATA: {clean_text}\n"
        except: return ""

    # Priority Pages
    target_urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # 1. Parallel Fetch (All URLs at once)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_url, target_urls))
        web_knowledge = "".join(results)

    # 2. Upload PDFs
    pdfs = []
    local_pdfs = glob.glob("*.pdf")
    for f in local_pdfs:
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # 3. Compile System Prompt (Pre-calc)
    system_instruction = f"""
    You are the Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    
    KNOWLEDGE BASE:
    {web_knowledge}
    
    STRICT RULES:
    1. **LANGUAGE**: Detect the language of the user's message. 
       - If English -> Respond in English.
       - If Spanish -> Respond in Spanish.
       
    2. **VIDEO REQUESTS**: If asking about videos/trends, reply: "Check our Knowledge Hub here: https://hcmakers.com/category-knowledge/"
    
    3. **CONTACT**: Plant: 752 N. Kent Road, Kent, IL | Phone: 847-258-0375.
    
    4. **ACCURACY**: Use the PDF tables for numbers (shelf life, protein, pack sizes). Do not hallucinate award numbers.
    
    5. **NO IMAGES**: Text only.
    """

    return system_instruction, pdfs

# --- 4. INITIALIZATION ---
# Load logic only runs once. Subsequent chats skip this.
with st.spinner("Connecting System..."):
    sys_prompt, ai_files = load_and_prepare_brain()

# Configure model with persistent instructions
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


# --- 6. INPUT & FAST RESPONSE ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    # Show User Input
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Generate Response
    with st.chat_message("assistant"):
        # We only send the Files + New Question (System prompt is already inside model)
        payload = ai_files + [prompt]
        
        try:
            # 1. "Thinking" Spinner appears for milliseconds
            with st.spinner("Thinking..."):
                stream = model.generate_content(payload, stream=True)
            
            # 2. Clean Stream (Removes Raw Data wrapper)
            def fast_stream_cleaner():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            # 3. Streamlit types out result immediately
            response = st.write_stream(fast_stream_cleaner)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("One moment, reconnecting...")