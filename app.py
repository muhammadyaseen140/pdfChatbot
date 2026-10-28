import streamlit as st
import streamlit.components.v1 as components
import json
import os
import uuid
from memory_creation_for_llm import update_vectorstore
from connect_memory_with_llm import get_qa_chain, condense_question
import database as db
from auth_ui import render_auth_page

# --- 1. Page Configuration ---
st.set_page_config(page_title="Enterprise Knowledge Base", page_icon="🤝", layout="wide")
db.init_db()

# --- 2. Session State for Chat ---
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

if not os.path.exists("data"):
    os.makedirs("data")

# --- 3. Dynamic CSS ---
st.markdown("""
    <style>
        /* Only the footer is hidden */
        footer {visibility: hidden;}
        
        /* Define Glow Colors based on Dark/Light */
        :root {
            --grid-glow-color: rgba(0, 229, 255, 0.2);
            --border-glow: #00e5ff;
        }
        @media (prefers-color-scheme: light) {
            :root {
                --grid-glow-color: rgba(0, 118, 255, 0.15);
                --border-glow: #0076ff;
            }
        }

        /* Apply Theme Colors to Main App */
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: var(--background-color) !important;
            color: var(--text-color) !important;
        }
        
        /* --- Sidebar Margin and Line Separation --- */
        [data-testid="stSidebar"] {
            background-color: var(--secondary-background-color) !important;
            border-right: 1px solid rgba(128, 128, 128, 0.25) !important;
        }
        [data-testid="stSidebar"] * {
            color: var(--text-color) !important;
        }
        
        /* Remove default top padding from sidebar */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0rem !important;
        }
        
        /* --- Sticky Sidebar Header (Company Name & Logo) --- */
        [data-testid="stSidebarUserContent"] > div:first-child {
            position: sticky;
            top: 0px;
            background-color: var(--secondary-background-color);
            z-index: 999;
            padding-top: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(128, 128, 128, 0.25);
            margin-bottom: 1rem;
        }
        
        /* --- Fix File Uploader Background, Font & Button in Dark Mode --- */
        [data-testid="stFileUploadDropzone"] {
            background-color: var(--secondary-background-color) !important;
            border: 1px dashed var(--border-glow) !important;
        }
        [data-testid="stFileUploadDropzone"] * {
            color: var(--text-color) !important;
        }
        [data-testid="stFileUploadDropzone"] button {
            background-color: transparent !important;
            color: var(--text-color) !important;
            border: 1px solid var(--border-glow) !important;
        }
        [data-testid="stFileUploadDropzone"] button:hover {
            background-color: var(--border-glow) !important;
            color: #fff !important;
        }
        
        /* --- Restored Prompt Input Animations & Fixed Red Border --- */
        [data-testid="stChatInputContainer"], 
        [data-testid="stChatInput"] {
            border: 2px solid var(--border-glow) !important;
            border-radius: 15px !important;
            background-color: var(--secondary-background-color) !important;
            box-shadow: 0 0 15px var(--grid-glow-color) !important;
            transition: all 0.3s ease !important;
            outline: none !important;
        }
        [data-testid="stChatInputContainer"]:focus-within,
        [data-testid="stChatInput"]:focus-within {
            box-shadow: 0 0 25px var(--border-glow), inset 0 0 10px var(--grid-glow-color) !important;
            transform: scale(1.015);
            border-color: var(--border-glow) !important;
            outline: none !important;
        }
        /* Removes Streamlit's internal red pseudo-element */
        [data-testid="stChatInput"]::after,
        [data-testid="stChatInput"]::before {
            display: none !important;
        }
        
        [data-testid="stChatInputTextArea"] textarea {
            background-color: transparent !important;
            color: var(--text-color) !important;
        }
        [data-testid="stChatInputTextArea"] textarea::placeholder {
            color: var(--text-color) !important;
            opacity: 0.6 !important;
        }
        
        /* Fix Bottom Bar (Chat Input Area) Background */
        [data-testid="stBottom"] > div {
            background-color: var(--background-color) !important;
        }
        
        /* General Text Color Fix */
        p, h1, h2, h3, h4, h5, h6, span, div {
            color: var(--text-color);
        }
        
        /* Attractive Buttons */
        .stButton>button {
            background: var(--secondary-background-color);
            color: var(--text-color) !important;
            border: 1px solid var(--border-glow);
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            transition: all 0.3s ease-in-out;
            font-weight: bold;
        }
        .stButton>button:hover {
            background: var(--border-glow);
            color: #fff !important;
            box-shadow: 0 0 20px var(--border-glow);
            transform: scale(1.02);
        }

        /* --- Jali (Grid) Animation Cards - ALWAYS ON --- */
        .cards-wrapper {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            margin-bottom: 30px;
            justify-content: center;
        }
        .jali-card {
            position: relative;
            background-color: var(--secondary-background-color);
            width: 30%;
            padding: 20px;
            border-radius: 12px;
            border: 2px solid rgba(128,128,128,0.2);
            overflow: hidden;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            transition: 0.3s ease;
        }
        .jali-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: 
                linear-gradient(var(--grid-glow-color) 1px, transparent 1px),
                linear-gradient(90deg, var(--grid-glow-color) 1px, transparent 1px);
            background-size: 15px 15px;
            z-index: 0;
            opacity: 1; /* Animation always runs */
            animation: scrollGrid 4s linear infinite;
        }
        @keyframes scrollGrid {
            0% { background-position: 0 0; }
            100% { background-position: 15px 15px; }
        }
        .jali-card:hover {
            border-color: var(--border-glow);
            box-shadow: 0 0 15px var(--border-glow), inset 0 0 20px var(--grid-glow-color);
            transform: translateY(-5px);
        }
        .card-content {
            position: relative;
            z-index: 1;
        }
        .card-icon { font-size: 2rem; margin-bottom: 10px; }
        .card-title { font-size: 1.1rem; font-weight: bold; color: var(--border-glow) !important; }
    </style>
""", unsafe_allow_html=True)

# --- Authentication gate: show sign in / sign up until the user is logged in ---
if not st.session_state.user:
    render_auth_page()
    st.stop()

user = st.session_state.user

# Load this user's saved chat history from the database (once per login)
if st.session_state.get('history_user_id') != user['id']:
    st.session_state.chat_history = db.get_chat_history(user['id'])
    st.session_state.history_user_id = user['id']

# --- API key / account menu ---
# The panel itself is a normal Streamlit popover. A small script adds an
# "API Key & Account" item to Streamlit's own top-right 3-dots menu that opens it.
# If the script cannot run, the "API Key" button stays visible (left of the Deploy button).
st.markdown("""
    <style>
        [data-testid="stPopover"] {
            position: fixed;
            top: 0.6rem;
            right: 13rem; /* Fallback position: left of the Deploy button */
            width: auto !important;
            z-index: 999999;
        }
        /* Once the 3-dots menu item is installed, hide the button and open the panel below the 3 dots */
        html[data-api-menu="1"] [data-testid="stPopover"] {
            right: 1.2rem;
            top: 3rem;
            opacity: 0;
            height: 1rem;
            overflow: hidden;
        }
    </style>
""", unsafe_allow_html=True)

MENU_SCRIPT = """
(function () {
    if (window.__apiMenuInstalled) { return; }
    window.__apiMenuInstalled = true;
    var doc = document;
    doc.documentElement.setAttribute('data-api-menu', '1');

    function isMenuOpen() {
        return !!doc.querySelector('[data-testid="stMainMenuList"]');
    }

    // Close Streamlit's 3-dots menu first, then call done()
    function closeMenu(done) {
        if (!isMenuOpen()) { done(); return; }
        var list = doc.querySelector('[data-testid="stMainMenuList"]');
        list.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true, cancelable: true
        }));
        var tries = 0, toggled = false;
        (function wait() {
            if (!isMenuOpen()) { setTimeout(done, 150); return; }
            tries += 1;
            if (tries === 6 && !toggled) {
                toggled = true;
                var menuButton = doc.querySelector('[data-testid="stMainMenu"]');
                if (menuButton) { menuButton.click(); }
            }
            if (tries > 20) { done(); return; }
            setTimeout(wait, 50);
        })();
    }

    // Open the single API Key / Account panel (only after the menu is closed)
    function openPanel() {
        closeMenu(function () {
            var trigger = doc.querySelector('[data-testid="stPopover"] button');
            if (trigger) { trigger.click(); }
        });
    }

    function addMenuItem() {
        var list = doc.querySelector('[data-testid="stMainMenuList"]');
        if (!list || list.querySelector('[data-custom-item="1"]')) { return; }
        var template = list.querySelector('[role="menuitem"]');
        if (!template) { return; }
        var item = template.cloneNode(true);
        item.setAttribute('data-custom-item', '1');
        var walker = doc.createTreeWalker(item, NodeFilter.SHOW_TEXT);
        var labelSet = false, node;
        while ((node = walker.nextNode())) {
            if (node.nodeValue.trim() === '') { continue; }
            node.nodeValue = labelSet ? '' : '\uD83D\uDD11 API Key & Account';
            labelSet = true;
        }
        if (!labelSet) { item.textContent = '\uD83D\uDD11 API Key & Account'; }
        item.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            openPanel();
        });
        list.insertBefore(item, list.firstChild);
    }

    new MutationObserver(addMenuItem).observe(doc.body, { childList: true, subtree: true });
})();
"""
try:
    components.html(
        "<script>var s = window.parent.document.createElement('script');"
        f"s.textContent = {json.dumps(MENU_SCRIPT)};"
        "window.parent.document.head.appendChild(s); s.remove();</script>",
        height=0,
    )
except Exception:
    pass  # The visible "API Key" button remains as a fallback

with st.popover("🔑 API Key"):
    key_input = st.text_input(
        "OpenAI API key",
        type="password",
        placeholder="sk-...",
        help="Stored only in this browser session. It is never saved to disk.",
    )
    if st.button("Save key", use_container_width=True):
        if key_input.strip():
            st.session_state.api_key = key_input.strip()
            st.cache_resource.clear()
            st.rerun()
        else:
            st.error("Please paste a key first.")
    if st.session_state.api_key or os.getenv("OPENAI_API_KEY"):
        st.success("API key is set ✅")
    else:
        st.warning("No API key set yet.")
    st.divider()
    st.caption(f"Signed in as **{user['name']}**  \n{user['email']}")
    if st.button("Sign out", use_container_width=True):
        for key in ('user', 'messages', 'chat_history', 'current_chat_id', 'api_key', 'history_user_id'):
            st.session_state.pop(key, None)
        st.session_state.auth_view = "signin"
        st.rerun()

# --- Functions ---
def clear_current_chat():
    # Data is saved automatically, so here we only clear the screen to avoid duplication.
    st.session_state.messages = []
    st.session_state.current_chat_id = None

# --- 4. Sidebar ---
with st.sidebar:
    st.title("🤝 Enterprise RAG")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ New Chat", use_container_width=True):
            clear_current_chat()
            st.rerun()
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            clear_current_chat()
            st.rerun()

    st.subheader("Data Upload")
    uploaded_files = st.file_uploader("Drop PDFs here", type="pdf", accept_multiple_files=True, label_visibility="collapsed")
    
    if st.button("Process Documents", use_container_width=True):
        if not uploaded_files:
            st.error("Please upload PDFs.")
        elif not (st.session_state.api_key or os.getenv("OPENAI_API_KEY")):
            st.error("Please add your OpenAI API key from the 🔑 menu at the top right.")
        else:
            with st.status("Updating internal memory...", expanded=True) as status:
                st.write("Saving files...")
                for file in uploaded_files:
                    with open(os.path.join("data", file.name), "wb") as f:
                        f.write(file.getbuffer())
                st.write("Generating embeddings...")
                success, msg = update_vectorstore(api_key=st.session_state.api_key or None)
                if success:
                    status.update(label="Database updated!", state="complete")
                    st.cache_resource.clear()
                else:
                    status.update(label=msg, state="error")

    if st.session_state.chat_history:
        st.divider()
        st.subheader("Chat History")
        for idx, chat in enumerate(reversed(st.session_state.chat_history)):
            # Each chat gets its own unique key
            if st.button(f"💬 {chat['title']}", key=f"hist_{chat['id']}", use_container_width=True):
                st.session_state.messages = chat['messages'].copy()
                st.session_state.current_chat_id = chat['id']
                st.rerun()

# --- 5. Main Chat Area ---
@st.cache_resource
def load_chain(api_key=None):
    try:
        return get_qa_chain(api_key)
    except Exception:
        return None

if not st.session_state.messages:
    st.markdown("<h2 style='text-align: center;'>How can I help you today?</h2>", unsafe_allow_html=True)
    
    st.markdown('''
    <div class="cards-wrapper">
        <div class="jali-card">
            <div class="card-content">
                <div class="card-icon">📁</div>
                <div class="card-title">Step 1</div>
                <div>Upload company PDFs from the sidebar.</div>
            </div>
        </div>
        <div class="jali-card">
            <div class="card-content">
                <div class="card-icon">⚙️</div>
                <div class="card-title">Step 2</div>
                <div>Click Process to train the AI memory.</div>
            </div>
        </div>
        <div class="jali-card">
            <div class="card-content">
                <div class="card-icon">💬</div>
                <div class="card-title">Step 3</div>
                <div>Ask anything in the chat box below.</div>
            </div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

prompt = st.chat_input("Ask a question based on your documents...")

if prompt:
    # Earlier messages of this chat, used as memory for follow-up questions
    history = st.session_state.messages.copy()

    with st.chat_message('user'):
        st.markdown(prompt)
    st.session_state.messages.append({'role': 'user', 'content': prompt})

    api_key = st.session_state.api_key or None
    qa_chain = load_chain(api_key)
    if not (api_key or os.getenv("OPENAI_API_KEY")):
        st.error("Please add your OpenAI API key from the 🔑 menu at the top right.")
    elif not qa_chain:
        st.error("Please process documents first.")
    else:
        with st.chat_message('assistant'):
            with st.spinner("Searching database..."):
                try:
                    standalone_question = condense_question(prompt, history, api_key)
                    response = qa_chain.invoke({'query': standalone_question})
                    st.markdown(response["result"])
                    st.session_state.messages.append({'role': 'assistant', 'content': response["result"]})
                    
                    # --- Auto-save logic ---
                    # If this is a new chat, generate a new ID and store it
                    if st.session_state.current_chat_id is None:
                        st.session_state.current_chat_id = str(uuid.uuid4())
                        title = prompt[:25] + "..."
                        st.session_state.chat_history.append({
                            "id": st.session_state.current_chat_id,
                            "title": title,
                            "messages": st.session_state.messages.copy()
                        })
                        db.save_chat(user['id'], st.session_state.current_chat_id, title, st.session_state.messages)
                    # If an older chat from the history is open, update that one
                    else:
                        for chat in st.session_state.chat_history:
                            if chat['id'] == st.session_state.current_chat_id:
                                chat['messages'] = st.session_state.messages.copy()
                                db.save_chat(user['id'], chat['id'], chat['title'], chat['messages'])
                                break

                except Exception as e:
                    st.error(f"Error: {str(e)}")