import streamlit as st
import sidebar
from config import MultiAgentOrchestrator

APP_TITLE = "Peacemaker Guild"
APP_VERSION = "0.3.0"


def greet():
    """Simple helper used by tests: reads `NAME` env var or defaults to 'World'."""
    import os
    name = os.getenv("NAME", "World")
    return f"Hello, {name}!"

# Page config
st.set_page_config(page_title=APP_TITLE, page_icon="🤖")

def render_app():
    st.title(f"🤖 {APP_TITLE}")

    # Initialize orchestrator once
    if "orchestrator" not in st.session_state:
        orch = MultiAgentOrchestrator()
        orch.load_config()  # loads servers, agent_styles, agents, moderator
        st.session_state["orchestrator"] = orch

    orch = st.session_state["orchestrator"]

    # Sidebar rendering
    with st.sidebar:
        sidebar.render_sidebar(orch, orch.agent_styles, orch.servers)

    # Messages state
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "system", "content": "You are a helpful AI assistant."}]

    # Render past messages
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        elif msg["role"] == "assistant":
            content = msg["content"]
            agent_name = None
            for name in orch.agent_styles.keys():
                if content.startswith(f"{name}:"):
                    agent_name = name
                    break
            if agent_name:
                style = orch.agent_styles[agent_name]
                st.chat_message("assistant").write(
                    f"{style['emoji']} **{agent_name}**\n\n"
                    f"<span style='color:{style['color']}'>{content[len(agent_name)+2:]}</span>",
                    unsafe_allow_html=True
                )
            else:
                st.chat_message("assistant").write(content)

    # Handle new input
    user_query = st.chat_input("Type a message")
    if user_query:
        st.chat_message("user").write(user_query)
        st.session_state["messages"].append({"role": "user", "content": user_query})
        st.session_state.setdefault("query_history", []).append(user_query)

        with st.spinner("Thinking..."):
            # Memory injection is handled inside `orch.chat` (per-agent and optional group memory)
            replies = orch.chat(user_query, st.session_state["messages"])

        for name, reply in replies.items():
            styled_reply = f"{name}: {reply}"
            st.session_state["messages"].append({"role": "assistant", "content": styled_reply})
            style = orch.agent_styles.get(name, {"emoji": "🤖", "color": "#000"})
            st.chat_message("assistant").write(
                f"{style['emoji']} **{name}**\n\n"
                f"<span style='color:{style['color']}'>{reply}</span>",
                unsafe_allow_html=True
            )

try:
    render_app()
except Exception as e:
    st.error(f"App error: {e}")

# Footer
try:
    st.markdown(f"---\n*{APP_TITLE} — v{APP_VERSION}*")
except Exception:
    pass
