import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re
import concurrent.futures
import time
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


# --- 3. HIGH-VELOCITY PRE-COMPUTED DATA ENGINE ---
@st.cache_resource(ttl=3600) 
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
            clean = re.sub(r'\s+', ' ', soup.get_text(separator=' ', strip=True))[:1500]
            return f"INFO[{url}]: {clean}\n"
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

    # Convert PDFs ONCE into permanent memory text
    pdf_files_in_directory = glob.glob("*.pdf")
    uploaded_gfiles =[]
    for file_name in pdf_files_in_directory:
        try: 
            uploaded = genai.upload_file(file_name)
            while uploaded.state.name == "PROCESSING":
                time.sleep(1)
                uploaded = genai.get_file(uploaded.name)
            uploaded_gfiles.append(uploaded)
        except: pass
        
    extracted_pdf_data = "No local specs loaded."
    if uploaded_gfiles:
        try:
            reader_model = genai.GenerativeModel('gemini-2.5-flash')
            req = uploaded_gfiles +["Extract all facts, nutrition specs, cheese variants, sizes (lb/oz), and pack sizes into detailed bullet points."]
            extracted_pdf_data = reader_model.generate_content(req).text
        except: pass

    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    
    LIVE DATA (WEBSITE): 
    {web_context}
    
    HARD DATA (SPECS):
    {extracted_pdf_data}
    
    *** CHAT RULES ***
    1. **LANGUAGE**: Output exactly matching user's language (Spanish or English).
    
    2. **CASUAL CONVERSATION**:
       - "Hi / Hello": "Hello! Welcome to Hispanic Cheese Makers. How can I help you today with our cheese products?" 
       - Compliments (wow, nice, interesting): Acknowledge politely and briefly without reciting long lists of cheese specs.

    3. **SALES HANDOFF**: 
       - IF a user asks a detailed question, asks about buying, ordering, pricing, or distributors:
       - **First**: Give the detailed specs/lineups. Do NOT stop your sentence short.
       - **Second**: Finish completely, provide 2 line breaks, and append: "\n\nTo learn how to become a customer, please contact our Sales Team here: https://hcmakers.com/contact-us/"
    
    4. **FACT CHECKING**: Stick to Data blocks. Videos are at: /category-knowledge/.
    5. **NO IMAGES**: Text conversations only.
    """
    return sys_instruction


# --- 4. ENGINE STARTUP ---
with st.spinner("Synchronizing specifications..."):
    sys_prompt = load_feather_brain()

# Removed size cap limits, allows full sentences to output!
config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1)

try:
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=sys_prompt,
        generation_config=config
    )
except:
    st.error("Failed to load Gemini.")
    st.stop()


# --- 5. UI CONTROLS & NEW JS SCROLL (Cross-Domain Fixed) ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history =[]

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def force_auto_scroll():
    # REMOVED "window.parent". Now exclusively targets Streamlit inner boundaries!
    # Timers trigger exactly as paragraphs expand so you don't miss text mid-generation.
    scroll_js = """
    <script>
        function goDown() {
            var chatInput = window.document.querySelector('.stChatInputContainer');
            var blockBox = window.document.querySelector('.main .block-container');
            if(chatInput) { chatInput.scrollIntoView({ behavior: 'smooth', block: 'end' }); }
            if(blockBox) { blockBox.scrollTop = blockBox.scrollHeight; }
        }
        goDown();
        setTimeout(goDown, 100);
        setTimeout(goDown, 500);
        setTimeout(goDown, 1000);
    </script>
    """
    components.html(scroll_js, height=0)


# --- 6. INSTANT INTERACTION LOOP ---
if prompt := st.chat_input("How can I help you? / ¿Cómo te puedo ayudar?"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                stream = model.generate_content([prompt], stream=True)
            
            def typing_speed():
                for chunk in stream:
                    if chunk.text: yield chunk.text

            response = st.write_stream(typing_speed)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
            # TRIGGER UPDATED SECURE AUTOSCROLL 
            force_auto_scroll()
            
        except:
            st.error("Connection pause. Please ask again.")