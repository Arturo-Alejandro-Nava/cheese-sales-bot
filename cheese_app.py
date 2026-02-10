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

# Universal Login Logic (Works on Local, Railway, Streamlit Cloud)
try:
    if "GOOGLE_API_KEY" in os.environ:
        API_KEY = os.environ["GOOGLE_API_KEY"]
    else:
        API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Critical Error: No API Key found.")
    st.stop()

genai.configure(api_key=API_KEY)


# --- 2. GUI / HEADER (Matches your Screenshot Design) ---
col1, col2, col3 = st.columns([1, 10, 1])
with col2:
    sub_col1, sub_col2, sub_col3 = st.columns([2, 1, 2])
    with sub_col2:
        # Detect logo (fallback safe)
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
# Updates Live Website Data every 2 Hours (TTL 7200). 
# This makes it INSTANT for 99.9% of requests.
@st.cache_resource(ttl=7200) 
def build_brain():
    # Speed Optimization: Session Reuse
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5)
    session.mount('https://', adapter)
    
    # 1. Scrape Logic
    def scrape_url(url):
        try:
            # 1.0 second Timeout. Fast or fail.
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=1.0)
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Clean "Bloat" (Scripts/Styles)
            for trash in soup(["script", "style", "nav", "footer", "iframe"]):
                trash.decompose()
            
            # Compress Text
            clean = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True))[:3000]
            return f"WEBSITE DATA [{url}]: {clean}\n"
        except: return ""

    # Live Website Targets
    urls = [
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    # Run all downloads simultaneously (Parallel)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_url, urls))
        web_context = "".join(results)

    # 2. Local PDF Loader
    pdfs = []
    # Reads ALL PDFs in the folder (make sure to upload the compressed ones!)
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # 3. STRICT SYSTEM PROMPT (The Guardrails)
    sys_instruction = f"""
    Role: Sales AI for "Hispanic Cheese Makers-Nuestro Queso".
    CONTEXT: {web_context}
    
    RULES:
    1. **LANGUAGE**: If User uses English -> Reply English. If Spanish -> Reply Spanish.
    2. **VIDEO**: Link to: https://hcmakers.com/category-knowledge/ (Do not invent YouTube links).
    3. **MEDALS/ACCURACY**: 
       - Do not hallucinate numbers. 
       - Use ONLY the provided website text above. 
       - If the text says "won Gold Medal" or "Award Winning", state that. 
       - DO NOT invent "21 medals in 7 years" unless you explicitly see it in the text provided.
    4. **SPECS**: Use the attached PDFs for accurate shelf-life/protein numbers.
    5. **NO IMAGES**.
    """
    
    return sys_instruction, pdfs


# --- 4. BOOT UP (Runs Once) ---
# This spinner handles the 3-second delay on first load.
# Everyone else skips this.
with st.spinner("Connected."):
    sys_prompt, ai_files = build_brain()

# Gemini Config: "Greedy" (Temp 0.0) for Max Logic Speed
model = genai.GenerativeModel(
    model_name='gemini-2.0-flash',
    system_instruction=sys_prompt,
    generation_config=genai.types.GenerationConfig(
        temperature=0.0,
        candidate_count=1
    )
)


# --- 5. CHAT HISTORY DISPLAY ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- 6. INSTANT INTERACTION LOOP ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    # Display User
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Generate Response
    with st.chat_message("assistant"):
        request_content = ai_files + [prompt]
        
        try:
            # "Thinking" Animation:
            # Because the brain is Cached (Loaded in RAM), this call is nearly instant.
            # The spinner flashes briefly, indicating "Thinking", then the text writes immediately.
            with st.spinner("Thinking..."):
                stream = model.generate_content(request_content, stream=True)
            
            # Pipe tokens directly to screen
            def immediate_yield():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(immediate_yield)
            
            # Save history
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
        except:
            st.error("Reconnecting...")