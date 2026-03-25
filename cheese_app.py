import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os
import glob
import re
import concurrent.futures
import time
import threading
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


# -------------------------------------------------------------
# 🔗 PASTE YOUR GOOGLE SCRIPT WEB APP URL HERE:
GOOGLE_SHEETS_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyaakBC7R8ErNlEgK4wc2aQdKBrT8IiamZr-YtxYDYLtXNZhQDfeAa3XzdLkm0P1Wul/exec"
# -------------------------------------------------------------


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
            req = uploaded_gfiles +["Extract all facts, nutrition specs, cheese variants, sizes (lb/oz), and pack sizes into detailed bullet points. Include ALL specific specs and facts from these sheets."]
            extracted_pdf_data = reader_model.generate_content(req).text
        except Exception as e:
            extracted_pdf_data = f"Fallback mode active."

    sys_instruction = f"""
    You are the Sales AI for Hispanic Cheese Makers-Nuestro Queso.
    
    LIVE DATA (WEBSITE): 
    {web_context}
    
    HARD DATA (FROM PDFs/SPEC SHEETS):
    {extracted_pdf_data}
    
    *** CRITICAL SALES STRATEGY & CHAT RULES ***
    1. **LANGUAGE**: Output in exactly the same language as user.
    
    2. **SMALL TALK PROTOCOL**:
       - User: "Hi / Hello". YOUR RESPONSE: "Hello! Welcome to Hispanic Cheese Makers. How can I help you today with our cheese products?" 
       - User comments generally (wow, nice, interesting). YOUR RESPONSE: Just warmly acknowledge and politely offer to help further (e.g. "I'm glad to hear! Are you interested in finding sizes for a specific product?"). NO data dumps!

    3. **CONSULTATIVE BUYER PATH**: 
       - If a user asks a detailed question, asks about lineages, buying, sizes, ordering, or distributors:
       - **First**: Address ALL questions fully based on the 'HARD DATA'.
       - **Second**: Finish your message entirely. Do not stop mid-sentence.
       - **Third**: Provide 2 line breaks, and at the very bottom end your answer with these exact words (Translate phrase exactly if conversing in Spanish):
         "\n\nTo learn how to become a customer, please contact our Sales Team here: https://hcmakers.com/contact-us/"
    
    4. **FACT CHECKING**: Only use facts from 'LIVE DATA' or 'HARD DATA' section above. Mention videos at: /category-knowledge/. No external URLs.
    5. **NO IMAGES**.
    """
    return sys_instruction


# --- 4. ENGINE STARTUP ---
with st.spinner("Synchronizing specifications..."):
    sys_prompt = load_feather_brain()

config = genai.types.GenerationConfig(temperature=0.0, candidate_count=1)

try:
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=sys_prompt,
        generation_config=config
    )
except Exception as e:
    st.error("Failed to load Gemini API connection.")
    st.stop()


# --- 5. UI CONTROLS ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history =[]

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def force_auto_scroll():
    scroll_js = """
    <script>
        function goDown() {
            var chatInput = window.parent.document.querySelector('.stChatInputContainer');
            var blockBox = window.parent.document.querySelector('.main .block-container');
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


# --- 6. BACKGROUND LOGGING FUNCTION ---
def save_log_to_sheets(user_q, ai_response):
    if "script.google.com" in GOOGLE_SHEETS_WEBHOOK_URL:
        try:
            # We send data strictly in the background
            requests.post(GOOGLE_SHEETS_WEBHOOK_URL, json={"user": user_q, "bot": ai_response})
        except: pass


# --- 7. INSTANT INTERACTION LOOP ---
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

            # Renders Text
            response = st.write_stream(typing_speed)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            autoscroll_down = force_auto_scroll()
            
            # FAST INVISIBLE CLOUD SAVE - (Triggers Thread to run post to google sheets in background without delaying bot UI)
            threading.Thread(target=save_log_to_sheets, args=(prompt, response)).start()
            
        except Exception as e:
            # Silent instant backup catch handling
            try:
                stream = model.generate_content([prompt], stream=True)
                def backup_speed():
                    for chunk in stream:
                        if chunk.text: yield chunk.text
                response = st.write_stream(backup_speed)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                force_auto_scroll()
                
                # Cloud Log Trigger
                threading.Thread(target=save_log_to_sheets, args=(prompt, response)).start()
            except:
                st.error("Connectivity pause. Resend your message please.")