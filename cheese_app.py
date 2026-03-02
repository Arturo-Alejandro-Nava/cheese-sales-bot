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
        
        /* Auto hides the Streamlit upper-right menu padding for clean embedding */
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


# --- 3. DATA ENGINE (High Logic + Casual Chat Mode) ---
@st.cache_resource(ttl=1800) 
def load_feather_brain():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    
    def scrape_light(url):
        try:
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
    
    # SYSTEM PROMPT: Updated with High-Intelligence Small Talk Directives
    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    LIVE DATA: {web_context}
    
    *** CRITICAL CONVERSATIONAL INTELLIGENCE ***
    
    1. **LANGUAGE LOCK (Highest Priority)**: 
       - IF Input is ENGLISH -> Reply in ENGLISH.
       - IF Input is SPANISH -> Reply in SPANISH.
       
    2. **GREETINGS & CASUAL REPLIES**:
       - IF user says "Hi", "Hello": **REPLY EXACTLY:** "Hello! Welcome to Hispanic Cheese Makers. How can I help you today with our cheese products?" 
       - IF user makes a statement (e.g. "that's interesting", "wow", "got it", "thank you", "cool"): 
         - Acknowledge them humanly. 
         - **REPLY EXAMPLE:** "I'm glad you found that helpful! Let me know if you want to know about our Queso Fresco, Oaxaca, or our pricing!"
       - **NEVER:** Spit out a massive paragraph of facts, videos, or company histories when responding to basic chit-chat or casual inputs. Say your casual response and stop typing.

    3. **SALES HANDOFF**: 
       - IF user asks to buy, requests pricing, bulk orders, or identifies as a distributor:
       - Answer product details thoroughly first.
       - THEN end the block with exactly: "\n\nTo learn how to become a customer, please contact our Sales Team here: https://hcmakers.com/contact-us/"
    
    4. **ACCURACY & NO HALLUCINATIONS**:
       - Never invent specs not listed in the PDF tables.
       - Refer only to URLs from the Live Data rules above (Docs -> /resources/ , Videos -> /category-knowledge/ ).
       
    5. **NO IMAGES**: Pure text conversations only.
    """
    return sys_instruction, pdfs


# --- 4. STARTUP (STRICT 2.5 FLASH ONLY) ---
with st.spinner("Connecting..."):
    sys_prompt, ai_files = load_feather_brain()

# A "greedy" search for temperature helps logical adherence for greetings
config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1)

# FORCED TO USE ONLY 2.5 FLASH. 
# Removing the 2.0 fallback because it approaches deprecation on Mar 31, 2026.
try:
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=sys_prompt,
        generation_config=config
    )
except Exception as e:
    # If the system breaks here, it throws a visible error rather than failing silently to an old model.
    st.error(f"Error loading the specific AI model (gemini-2.5-flash). Please check API parameters. Log: {e}")
    st.stop()


# --- 5. UI: CACHED MEMORY ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history =[]

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# JavaScript Tool to force your container/webpage to track to the very bottom.
def autoscroll_down():
    components.html(
        f"""
            <script>
                // Auto-scrolls the view when rendering finishes inside the Iframe.
                window.parent.scrollTo(0, window.parent.document.body.scrollHeight);
                const scrolling_target = window.parent.document.querySelector('.stChatInputContainer');
                if(scrolling_target) {{ scrolling_target.scrollIntoView({{ behavior: "smooth" }}); }}
            </script>
        """, height=0
    )


# --- 6. INSTANT INTERACTIVE INPUT ---
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
            
            # TRIGGER SCROLL-TO-BOTTOM JS 
            autoscroll_down()
            
        except Exception as e:
            # Retry connection seamlessly without UI disruption 
            try:
                stream = model.generate_content(req_content, stream=True)
                def retry_yield():
                    for chunk in stream:
                        if chunk.text: yield chunk.text
                response = st.write_stream(retry_yield)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                autoscroll_down() 
            except:
                st.error("Server connection took too long. Try resending.")