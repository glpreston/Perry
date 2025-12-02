# sidebar.py
import re
import io
import csv
import json
import datetime
import streamlit as st
from pathlib import Path
from config import get_models_for_server

CONFIG_PATH = Path("agents_config.json")

def render_sidebar(orch, agent_styles, servers):
    st.header("⚙️ Control Panel")
    # --- Per-agent controls ---
    agent_names = list(orch.agents.keys())
    server_names = list(servers.keys())

    for name in agent_names:
        emoji = agent_styles.get(name, {}).get("emoji", "🤖")
        # Sanitize name for use in Streamlit widget keys
        safe_name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
        # Use an expander per agent for a compact layout
        with st.expander(f"{emoji} {name}", expanded=(name == getattr(orch, "active_agent", None))):
            sel_agent = orch.agents[name]

            # Determine the current server selection for this agent (match by host)
            agent_host = getattr(sel_agent, "host", None)
            current_server_name = server_names[0]
            for sname, h in servers.items():
                if h == agent_host:
                    current_server_name = sname
                    break

            selected_server = st.selectbox(
                "Server",
                server_names,
                index=server_names.index(current_server_name) if current_server_name in server_names else 0,
                key=f"server_{safe_name}",
            )
            # Update the agent's host based on the selected server
            sel_agent.host = servers[selected_server]

            # Models are dynamic per server; fall back to the agent's configured model
            models = get_models_for_server(sel_agent.host) or []
            if not models:
                st.info("No models available for the selected server.")
                # Clear the agent model to indicate none selected
                sel_agent.model = ""
            else:
                current_model_index = 0
                if getattr(sel_agent, "model", None) in models:
                    current_model_index = models.index(sel_agent.model)

                selected_model = st.selectbox(
                    "Model",
                    models,
                    index=current_model_index,
                    key=f"model_{safe_name}",
                )
                sel_agent.model = selected_model

    # Ensure global active_server/model reflect the currently active agent (if any)
    if getattr(orch, "active_agent", None) in agent_names:
        active = orch.active_agent
        orch.active_server = next((k for k, v in servers.items() if v == getattr(orch.agents[active], "host", None)), None)
        orch.active_model = getattr(orch.agents[active], "model", None)

    # --- Moderator toggle + status indicator ---
    use_moderator = st.checkbox("Use Moderator", value=orch.use_moderator)
    orch.use_moderator = use_moderator
    orch.set_moderator()

    if use_moderator:
        st.markdown("✅ **Moderator active**")
    else:
        st.markdown("🚫 **Moderator muted**")

    # --- Memory toggle ---
    use_memory = st.checkbox("Use Memory", value=orch.use_memory)
    orch.set_memory_usage(use_memory)

    # --- Group Memory toggle ---
    use_group_memory = st.checkbox("Use Group Memory", value=getattr(orch, "use_group_memory", False))
    orch.use_group_memory = use_group_memory

    # --- Memory DB status indicator ---
    db = getattr(orch, "memory_db", None)
    if db:
        try:
            connected = db.is_connected()
        except Exception:
            connected = False
        status_emoji = "🟢" if connected else "🔴"
        st.markdown(f"**Memory DB:** {status_emoji} {'Connected' if connected else 'Disconnected'}")
    else:
        st.markdown("**Memory DB:** ⚪ Not configured")

    # --- Save / Load Config ---
    cols = st.columns(2)
    if cols[0].button("💾 Save Config"):
        orch.save_config(CONFIG_PATH)
        st.toast("Configuration saved!", icon="✅")
    if cols[1].button("📂 Load Config"):
        orch.load_config(CONFIG_PATH)
        st.toast("Configuration loaded!", icon="📂")
        # Refresh Streamlit app to reflect newly-loaded config immediately
        try:
            st.experimental_rerun()
        except Exception:
            # If rerun isn't possible (e.g. during testing), continue silently
            pass

    # --- Recent Queries ---
    st.markdown("### 🕑 Recent Queries")
    for q in st.session_state.get("query_history", [])[-5:][::-1]:
        st.write(f"- {q}")

    # (Per-agent updates already applied above.)

    # --- Memory Inspector ---
    db = getattr(orch, "memory_db", None)
    with st.expander("🔎 Memory Inspector", expanded=False):
        if not db:
            st.info("Memory DB not configured — no memories to inspect.")
        else:
            options = ["__group__"] + list(orch.agents.keys())
            sel = st.selectbox("Show memories for", options, index=0, key="mem_inspector_select")
            try:
                qa_list = db.load_recent_qa(None if sel == "__group__" else sel, limit=10)
                if not qa_list:
                    st.write("No QA entries found.")
                else:
                    for item in qa_list:
                        q = item.get("q", "")
                        a = item.get("a", "")
                        ts = item.get("ts")
                        st.markdown(f"**Q:** {q}  \n**A:** {a}  \n*{ts}*")
                        st.write("---")

                # Export memories for the selected key
                st.markdown("**Export memories**")
                out_format = st.selectbox("Format", ["csv", "json"], index=0, key=f"export_format_{sel}")
                limit = st.number_input("Max rows", min_value=1, max_value=10000, value=100, step=10, key=f"export_limit_{sel}")

                if st.button("Prepare export", key=f"prepare_export_{sel}"):
                    try:
                        rows = db.load_recent_qa(None if sel == "__group__" else sel, limit=int(limit))
                        # Normalize
                        normalized = []
                        for r in rows:
                            nr = dict(r)
                            nr['agent_name'] = (r.get('agent_name') or r.get('agent') or ('__group__' if sel == '__group__' else sel))
                            normalized.append(nr)

                        timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                        fname = f"{sel}_memories_{timestamp}.{out_format}"

                        if out_format == 'csv':
                            buf = io.StringIO()
                            writer = csv.writer(buf)
                            writer.writerow(['agent_name', 'question', 'answer', 'conv_id', 'timestamp'])
                            for r in normalized:
                                writer.writerow([
                                    r.get('agent_name',''),
                                    r.get('q') or r.get('question',''),
                                    r.get('a') or r.get('answer',''),
                                    r.get('conv_id') or r.get('conv',''),
                                    r.get('ts') or r.get('timestamp','')
                                ])
                            data = buf.getvalue().encode('utf-8')
                        else:
                            data = json.dumps(normalized, default=str, ensure_ascii=False, indent=2).encode('utf-8')

                        st.download_button("Download export", data, file_name=fname, mime='text/csv' if out_format=='csv' else 'application/json')
                    except Exception as e:
                        st.error(f"Export failed: {e}")

                # Clear memories (two-step confirmation)
                clear_flag_key = f"confirm_clear_{sel}"
                if st.button("Clear memories for selected", key=f"clear_btn_{sel}"):
                    st.session_state[clear_flag_key] = True

                if st.session_state.get(clear_flag_key, False):
                    st.warning("This will permanently delete memories for the selected entry. This action cannot be undone.")
                    if st.button("Confirm delete", key=f"confirm_del_{sel}"):
                        try:
                            target = None if sel == "__group__" else sel
                            # Use clear_memory with the agent/group key
                            db.clear_memory("__group__" if sel == "__group__" else sel)
                            st.success("Memories cleared.")
                            st.session_state[clear_flag_key] = False
                            # Try to trigger a rerun; if Streamlit doesn't expose experimental_rerun,
                            # fall back to asking the user to manually refresh the page.
                            try:
                                if hasattr(st, "experimental_rerun"):
                                    st.experimental_rerun()
                                else:
                                    st.info("Please refresh the page to see the changes.")
                            except Exception:
                                st.info("Please refresh the page to see the changes.")
                        except Exception as e:
                            st.error(f"Failed to clear memories: {e}")
            except Exception as e:
                st.error(f"Error loading memories: {e}")

    # --- Clear All Memories (destructive) ---
    if db:
        with st.expander("⚠️ Clear All Memories (destructive)", expanded=False):
            st.write("This will permanently delete all rows from the `agent_memory` table for all agents and group memory.")
            st.write("Strongly recommended: export your memories before running this.")
            export_before = st.checkbox("Export all memories before clearing", value=True, key="export_all_before_clear")

            if export_before and st.button("Prepare full export", key="prepare_full_export"):
                try:
                    # Attempt to read all rows from the table
                    rows = db._try_execute("SELECT agent_name, question, answer, conv_id, timestamp FROM agent_memory ORDER BY timestamp DESC LIMIT 100000", (), fetch=True)
                    if not rows:
                        st.info("No rows found to export.")
                    else:
                        # Convert to CSV in-memory
                        import io, csv
                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        writer.writerow(['agent_name', 'question', 'answer', 'conv_id', 'timestamp'])
                        for agent_name, q, a, conv_id, ts in rows:
                            writer.writerow([agent_name or '', q or '', a or '', conv_id or '', ts or ''])
                        data = buf.getvalue().encode('utf-8')
                        fname = f"all_memories_export_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
                        st.download_button("Download full export", data, file_name=fname, mime='text/csv')
                except Exception as e:
                    st.error(f"Failed to prepare full export: {e}")

            clear_all_flag = st.session_state.get('confirm_clear_all', False)
            if st.button("Clear ALL memories (permanent)", key="clear_all_btn"):
                st.session_state['confirm_clear_all'] = True

            if st.session_state.get('confirm_clear_all', False):
                st.warning("This will PERMANENTLY delete ALL memories. This action cannot be undone.")
                confirm_text = st.text_input("Type DELETE ALL to confirm", key="confirm_all_text")
                if confirm_text == "DELETE ALL":
                    if st.button("Confirm delete ALL", key="confirm_del_all"):
                        try:
                            db.clear_all()
                            st.success("All memories cleared.")
                            st.session_state['confirm_clear_all'] = False
                            try:
                                if hasattr(st, "experimental_rerun"):
                                    st.experimental_rerun()
                                else:
                                    st.info("Please refresh the page to see the changes.")
                            except Exception:
                                st.info("Please refresh the page to see the changes.")
                        except Exception as e:
                            st.error(f"Failed to clear all memories: {e}")
                else:
                    st.info("Type the exact phrase 'DELETE ALL' to enable the final confirmation button.")

