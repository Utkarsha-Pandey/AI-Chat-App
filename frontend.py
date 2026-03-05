import streamlit as st
import requests

API_URL = "http://localhost:8000"

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Nexus AI", 
    page_icon="💠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (UI POLISH) ---
st.markdown("""
<style>
    /* Hide default Streamlit clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Modern Gradient Title */
    .main-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(135deg, #60A5FA, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0px;
        padding-top: 2rem;
    }
    
    .sub-title {
        text-align: center;
        color: #94A3B8;
        font-size: 1.1rem;
        margin-bottom: 3rem;
        font-weight: 400;
    }

    /* Elegant Login Card */
    .login-box {
        background-color: #1E293B;
        padding: 3rem;
        border-radius: 16px;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    
    /* Sleek Sidebar Header */
    .sidebar-title {
        color: #60A5FA;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if "token" not in st.session_state:
    st.session_state["token"] = None
if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = None

def get_headers():
    return {"Authorization": f"Bearer {st.session_state['token']}"}

# --- LOGIN / SIGN UP SCREEN ---
if not st.session_state["token"]:
    st.markdown('<p class="main-title">💠 Nexus AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Your intelligent workspace.</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Secure Login", "Create Account"])
        
        with tab1:
            st.write("<br>", unsafe_allow_html=True)
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            st.write("<br>", unsafe_allow_html=True)
            
            if st.button("Authenticate", use_container_width=True, type="primary"):
                response = requests.post(f"{API_URL}/login", data={"username": email, "password": password})
                if response.status_code == 200:
                    st.session_state["token"] = response.json()["access_token"]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                    
        with tab2:
            st.write("<br>", unsafe_allow_html=True)
            new_email = st.text_input("Email Address", key="reg_email")
            new_password = st.text_input("Password", type="password", key="reg_pass")
            st.write("<br>", unsafe_allow_html=True)
            
            if st.button("Register", use_container_width=True, type="primary"):
                response = requests.post(f"{API_URL}/users/", json={"email": new_email, "password": new_password})
                if response.status_code == 201:
                    st.success("Account successfully created. Please log in.")
                elif response.status_code == 400:
                    st.error("Email is already in use.")
                else:
                    st.error("Registration failed.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN CHAT APP ---
else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown('<div class="sidebar-title">💠 Nexus</div>', unsafe_allow_html=True)
        
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            res = requests.post(f"{API_URL}/chats/", json={"title": "New Conversation"}, headers=get_headers())
            if res.status_code == 200:
                st.session_state["current_session_id"] = res.json()["id"]
                st.rerun()
                
        st.write("<br>", unsafe_allow_html=True)
        st.caption("RECENT")

        res = requests.get(f"{API_URL}/chats/", headers=get_headers())
        if res.status_code == 200:
            sessions = res.json()
            if not sessions:
                st.info("No active sessions.")
            else:
                for session in reversed(sessions):
                    is_active = session['id'] == st.session_state["current_session_id"]
                    btn_type = "primary" if is_active else "secondary"
                    
                    if st.button(f"💬 {session['title']}", key=f"session_{session['id']}", use_container_width=True, type=btn_type):
                        st.session_state["current_session_id"] = session["id"]
                        st.rerun()

        st.divider()
        if st.button("Log Out", use_container_width=True):
            st.session_state["token"] = None
            st.session_state["current_session_id"] = None
            st.rerun()

    # --- MAIN WINDOW ---
    if st.session_state["current_session_id"]:
        session_id = st.session_state["current_session_id"]
        
        msg_res = requests.get(f"{API_URL}/chats/{session_id}/messages", headers=get_headers())
        
        if msg_res.status_code == 200:
            messages = msg_res.json()
            
            # Custom Avatars for the chat bubbles
            avatar_map = {"user": "👤", "assistant": "💠"}
            
            for msg in messages:
                with st.chat_message(msg["role"], avatar=avatar_map.get(msg["role"], "💬")):
                    st.write(msg["content"])
        
        if prompt := st.chat_input("Send a message to Nexus..."):
            
            # 1. Instantly display the user's message
            with st.chat_message("user", avatar="👤"):
                st.write(prompt)
                
            # 2. Show the streaming AI response
            with st.chat_message("assistant", avatar="💠"):
                response_placeholder = st.empty()
                full_response = ""
                
                payload = {"role": "user", "content": prompt}
                
                # Make a streaming POST request to the new endpoint
                try:
                    with requests.post(
                        f"{API_URL}/chats/{session_id}/messages/stream", 
                        json=payload, 
                        headers=get_headers(), 
                        stream=True
                    ) as r:
                        if r.status_code == 200:
                            for chunk in r.iter_content(chunk_size=None):
                                if chunk:
                                    # Decode the chunk and append to the full response
                                    decoded_chunk = chunk.decode("utf-8")
                                    full_response += decoded_chunk
                                    # Update the placeholder with the current text + a blinking block
                                    response_placeholder.write(full_response + "▌")
                            
                            # Final write to remove the block cursor once the stream is done
                            response_placeholder.write(full_response)
                        else:
                            st.error(f"Failed to fetch response: {r.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

    else:
        st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: #F8FAFC; font-weight: 600;">How can I assist you?</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #64748B;">Select a conversation or start a new one.</p>', unsafe_allow_html=True)