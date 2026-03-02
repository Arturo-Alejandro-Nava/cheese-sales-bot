import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re
import concurrent.futures

# Allows injecting the Auto-Scroll Script
import streamlit.components.v1 as components 

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
        possible_names =["logo_new.png", "logo_new.jpg", "logo.jpg", "logo.png", "logo"]
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
        
        /* Auto hides the Streamlit menu and paddings for clean embedding */
        #MainMenu {visibility: hidden;} 
        header {visibility: hidden;}
        </style>
        <div class="header-text">
            <div class="line-one">Hispanic Cheese Makers</div>
            <div class="line-two">Nuestro Queso</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
st.markdown("---")


# --- 3. DATA ENGINE (Live Cache & Context Switcher) ---
@st.cache_resource(ttl=1800) 
def load_feather_brain():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    
    def scrape_light(url):
        try:
            # High aggression 0.8s timeout
            r = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=0.8)
            soup = BeautifulSoup(r.content, 'html.parser')
            for trash in soup(["script", "style", "nav", "footer", "form", "svg", "iframe"]):
                trash.decompose()
            text = soup.get_text(separator=' ', strip=True)
            clean = re.sub(r'\s+', ' ', text)[:1500]
            return f"INFO [{url}]: {clean}\n"
        except: return ""

    urls =[
        "https://hcmakers.com/", 
        "https://hcmakers.com/about-us/", 
        "https://hcmakers.com/products/", 
        "https://hcmakers.com/contact-us/",
        "https://hcmakers.com/category-knowledge/"
    ]
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(scrape_light, urls))
        web_context = "".join(results)

    pdfs =[]
    for f in glob.glob("*.pdf"):
        try: pdfs.append(genai.upload_file(f))
        except: pass
    
    # FAST-SYSTEM INSTRUCTIONS
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    LIVE DATA: {web_context}
    
    *** OPERATIONAL PROTOCOLS ***
    1. **LANGUAGE**: Keep response matching exactly the user language. Do not mix them.
    
    2. **CASUAL RESPONSES (CRITICAL)**: 
       - IF user inputs basic words ("Hi", "Thanks", "Interesting", "Wow", "Good to know"): 
       - Respond simply in one single brief sentence. Acknowledge and politely offer more help. Do NOT write paragraphs about the company!
    
    3. **SALES HANDOFF**: 
       - If they indicate intent to purchase or be a wholesale buyer:
       - Explain the products briefly, THEN drop this at the bottom: 
         "\n\nTo learn how to become a customer, please contact our Sales Team here: https://hcmakers.com/contact-us/"
         
    4. **NO HALLUCINATIONS**: Read exact facts provided from text/docs. (21 awards, link /category-knowledge/ for videos).
    """
    return sys_instruction, pdfs


# --- 4. STARTUP (Gemini 2.5 FLASH STRICT) ---
with st.spinner("Connecting..."):
    sys_prompt, ai_files = load_feather_brain()

# 'Greedy decoding' for Max computational return velocity, capping length to stop rambling
config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1, max_output_tokens=400)

try:
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=sys_prompt,
        generation_config=config
    )
except Exception as e:
    st.error(f"Critical System Loading Error: {e}")
    st.stop()


# --- 5. UI: HISTORY LOG ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history =[]

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- UI SCROLL UTILITY ---
def autoscroll_down():
    components.html(
        f"""
            <script>
                // Snaps Streamlit UI downwards continuously to remain attached to text rendering
                window.parent.scrollTo(0, window.parent.document.body.scrollHeight);
            </script>
        """, height=0
    )


# --- 6. INTELLIGENT PAYLOAD CONTROLLER & INPUT ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        
        # SMART ROUTING - (THE REASON IT IS FAST)
        # Scan if question requires complex spec math using Regular Expressions (bilingual tracking)
        heavy_data_triggers = re.compile(r'protein|fat|size|lb|oz|peso|tamaño|nutrit|ingred|grasa|shelf life', re.IGNORECASE)
        
        # If words exist -> Use AI PDFs (Slower, ~3sec)
        # If words dont -> Send only Prompt & Web Knowledge (Instantaneous, ~0.5s)
        if heavy_data_triggers.search(prompt):
            req_content = ai_files + [prompt]
        else:
            req_content = [prompt]
        
        try:
            with st.spinner("Thinking..."):
                stream = model.generate_content(req_content, stream=True)
            
            def stream_data():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            # Visual typewriter effect onto user interface 
            response = st.write_stream(stream_data)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
            # Anchor window view natively downward. 
            autoscroll_down() 
            
        except Exception:
            # Fallback auto-refresh without user noticing red lines immediately.
            try:
                stream = model.generate_content(req_content, stream=True)
                def rt_stream():
                    for c in stream:
                        if c.text: yield c.text
                res = st.write_stream(rt_stream)
                st.session_state.chat_history.append({"role":"assistant", "content": res})
                autoscroll_down()
            except:
                st.error("Signal disrupted, please ask that one more time.")