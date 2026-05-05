import streamlit as st
import json
import os
from datetime import datetime
from yt_chatbot_backend import get_transcript, create_chain, get_answer

# Page config
st.set_page_config(
    page_title="YouTube Video Chatbot",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 0;
    }
    
    .header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 20px;
    }
    
    .history-item {
        padding: 12px;
        margin: 8px 0;
        background-color: #e3f2fd;
        border-radius: 6px;
        cursor: pointer;
        border-left: 3px solid #667eea;
        transition: all 0.2s;
        font-size: 13px;
        word-break: break-word;
    }
    
    .history-item:hover {
        background-color: #bbdefb;
        border-left: 3px solid #764ba2;
    }
    
    .chat-message-user {
        background-color: #667eea;
        color: white;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
        text-align: right;
        margin-left: 20%;
    }
    
    .chat-message-bot {
        background-color: #f5f5f5;
        color: #333;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
        margin-right: 20%;
    }
    
    .success-text {
        color: #4caf50;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# History file for persistence
HISTORY_FILE = "chat_sessions.json"

def load_sessions():
    """Load all chat sessions from file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sessions(sessions):
    """Save all chat sessions to file"""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        st.error(f"Could not save sessions: {e}")

# Initialize session state
if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions()

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

if "current_video_id" not in st.session_state:
    st.session_state.current_video_id = ""

if "chain" not in st.session_state:
    st.session_state.chain = None

if "video_loaded" not in st.session_state:
    st.session_state.video_loaded = False

# Header
st.markdown("<div class='header'><h1>🎥 YouTube Video Chatbot</h1><p>Ask questions about any YouTube video</p></div>", 
            unsafe_allow_html=True)

# Main layout
col1, col2 = st.columns([1, 2.5], gap="large")

# ============= LEFT COLUMN - VIDEO INPUT & HISTORY =============
with col1:
    st.markdown("### 📹 Load Video")
    
    video_id_input = st.text_input(
        "YouTube Video ID",
        placeholder="e.g., Gfr50f6ZBvo",
        help="Find ID in URL after 'v='",
        key="video_id_input"
    )
    
    load_btn = st.button("Load Video", use_container_width=True, type="primary")
    
    if load_btn and video_id_input.strip():
        st.session_state.current_video_id = video_id_input.strip()
        
        # Create new session
        session_id = f"video_{st.session_state.current_video_id}_{datetime.now().timestamp()}"
        st.session_state.current_session_id = session_id
        st.session_state.sessions[session_id] = {
            "video_id": st.session_state.current_video_id,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }
        
        # Load transcript and create chain
        with st.spinner("Fetching transcript..."):
            try:
                transcript = get_transcript(st.session_state.current_video_id)
                st.session_state.chain = create_chain(transcript)
                st.session_state.video_loaded = True
                save_sessions(st.session_state.sessions)
                st.success("✓ Video loaded!")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.session_state.video_loaded = False
    
    st.divider()
    
    # Display video status
    if st.session_state.video_loaded:
        st.markdown(f"<p class='success-text'>✓ Video ID: {st.session_state.current_video_id}</p>", 
                   unsafe_allow_html=True)
    
    st.divider()
    
    # Chat History
    st.markdown("### 📚 Chat History")
    
    if st.session_state.sessions:
        for session_id, session in reversed(list(st.session_state.sessions.items())):
            created = datetime.fromisoformat(session["created_at"]).strftime("%m/%d %H:%M")
            msg_count = len(session["messages"])
            
            col_history, col_delete = st.columns([4, 1])
            
            with col_history:
                if st.button(
                    f"🎥 {session['video_id'][:20]}\n{created} ({msg_count} msgs)",
                    key=f"history_{session_id}",
                    use_container_width=True
                ):
                    st.session_state.current_session_id = session_id
                    st.session_state.current_video_id = session["video_id"]
                    st.session_state.video_loaded = True
                    
                    # Reload chain
                    with st.spinner("Loading..."):
                        try:
                            transcript = get_transcript(session["video_id"])
                            st.session_state.chain = create_chain(transcript)
                        except:
                            st.warning("Could not reload video")
                    
                    st.rerun()
            
            with col_delete:
                if st.button("🗑️", key=f"delete_{session_id}", use_container_width=True):
                    del st.session_state.sessions[session_id]
                    save_sessions(st.session_state.sessions)
                    if st.session_state.current_session_id == session_id:
                        st.session_state.current_session_id = None
                        st.session_state.video_loaded = False
                    st.rerun()
    else:
        st.info("No chat history yet")

# ============= RIGHT COLUMN - CHAT =============
with col2:
    st.markdown("### 💬 Chat")
    
    if st.session_state.video_loaded and st.session_state.current_session_id:
        current_session = st.session_state.sessions[st.session_state.current_session_id]
        
        # Display chat messages
        chat_container = st.container(height=400, border=True)
        
        with chat_container:
            if current_session["messages"]:
                for msg in current_session["messages"]:
                    if msg["role"] == "user":
                        st.markdown(
                            f'<div class="chat-message-user"><b>You:</b><br>{msg["content"]}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="chat-message-bot"><b>Bot:</b><br>{msg["content"]}</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.markdown(
                    '<p style="text-align: center; color: #999; margin-top: 150px;">No messages yet. Ask your first question!</p>',
                    unsafe_allow_html=True
                )
        
        st.divider()
        
        # Input area
        col_input, col_send = st.columns([5, 1])
        
        with col_input:
            user_input = st.text_input(
                "Ask a question",
                placeholder="What is this video about?",
                key="user_question"
            )
        
        with col_send:
            send_btn = st.button("Send", use_container_width=True, type="primary")
        
        # Process input
        if send_btn and user_input.strip():
            # Add user message
            current_session["messages"].append({
                "role": "user",
                "content": user_input
            })
            
            # Get bot response
            with st.spinner("Thinking..."):
                try:
                    response = get_answer(st.session_state.chain, user_input)
                    
                    # Add bot message
                    current_session["messages"].append({
                        "role": "bot",
                        "content": response
                    })
                    
                    save_sessions(st.session_state.sessions)
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    else:
        # Empty state
        st.markdown("""
        <div style='text-align: center; padding: 100px 20px;'>
            <h3>👈 Start by loading a video</h3>
            <p style='color: #999;'>
                1. Enter a YouTube Video ID on the left<br>
                2. Click "Load Video"<br>
                3. Ask questions about the video
            </p>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #999; font-size: 12px; padding: 10px;'>
    <p>YouTube Video Chatbot | RAG powered by LangChain & OpenAI</p>
</div>
""", unsafe_allow_html=True)