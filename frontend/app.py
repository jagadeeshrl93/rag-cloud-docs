import os
import streamlit as st
import httpx
from pathlib import Path

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="RAG Cloud Docs",
    page_icon="🔍",
    layout="wide",
)

# ── Initialise session state ──────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if "view" not in st.session_state:
    st.session_state.view = "home"  # "home" or "chat"

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = []  # list of {question, answer, sources, model, chunks_used}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("RAG Cloud Docs")

    # Back to home button — only show when in chat view
    if st.session_state.view == "chat":
        if st.button("← New question", use_container_width=True):
            st.session_state.view = "home"
            st.session_state.messages = []
            st.session_state.pending_question = None
            st.rerun()

    st.divider()

    # Documents section
    st.subheader("Documents")
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "md", "txt", "html"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        for uploaded_file in uploaded_files:
            file_path = data_dir / uploaded_file.name
            file_path.write_bytes(uploaded_file.getvalue())
        st.success(f"{len(uploaded_files)} file(s) uploaded")

    if st.button("Ingest documents", use_container_width=True, type="primary"):
        with st.spinner("Ingesting..."):
            try:
                response = httpx.post(
                    f"{API_BASE}/ingest",
                    json={"directory": "data", "clear_existing": True},
                    timeout=120.0,
                )
                result = response.json()
                st.success(
                    f"{result['chunks_stored']} chunks · "
                    f"{result['documents_loaded']} doc(s)"
                )
            except Exception as e:
                st.error(f"Failed: {e}")

    st.divider()

    # Settings
    st.subheader("Settings")
    top_k = st.slider("Chunks to retrieve", min_value=1, max_value=10, value=5)

    # API status
    try:
        httpx.get(f"{API_BASE}/health", timeout=3.0)
        st.caption("🟢 API running")
    except Exception:
        st.caption("🔴 API not running")

    st.divider()

    # Chat history
    if st.session_state.chat_sessions:
        st.subheader("History")
        for i, session in enumerate(reversed(st.session_state.chat_sessions)):
            # Truncate long questions for display
            label = session["question"]
            if len(label) > 40:
                label = label[:40] + "..."
            if st.button(label, key=f"history_{i}", use_container_width=True):
                # Load this session into the chat view
                st.session_state.messages = [
                    {"role": "user", "content": session["question"]},
                    {
                        "role": "assistant",
                        "content": session["answer"],
                        "sources": session["sources"],
                        "chunks_used": session["chunks_used"],
                        "model": session["model"],
                    },
                ]
                st.session_state.view = "chat"
                st.rerun()

        if st.button("Clear history", use_container_width=True):
            st.session_state.chat_sessions = []
            st.session_state.messages = []
            st.session_state.view = "home"
            st.rerun()


# ── Helper: call the API and return result ────────────────────────────────────
def ask_question(question: str) -> dict | None:
    try:
        response = httpx.post(
            f"{API_BASE}/query",
            json={"question": question, "top_k": top_k},
            timeout=60.0,
        )
        return response.json()
    except httpx.ConnectError:
        st.error("Cannot connect to API. Make sure uvicorn is running.")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


# ── Helper: render a single answer ───────────────────────────────────────────
def render_answer(result: dict):
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    chunks_used = result.get("chunks_used", 0)
    model = result.get("model", "unknown")

    st.markdown(answer)

    if sources:
        with st.expander("Sources"):
            for source in sources:
                st.caption(f"📄 {source}")

    st.caption(f"Chunks used: {chunks_used} · Model: {model}")
    return answer, sources, chunks_used, model


# ── HOME VIEW ─────────────────────────────────────────────────────────────────
if st.session_state.view == "home":
    st.title("RAG Cloud Docs")
    st.caption("Ask questions about your cloud infrastructure documentation")

    st.info(
        "Upload documents in the sidebar, click **Ingest documents**, "
        "then ask a question below."
    )

    # Example question buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(
            "How do I rotate AWS IAM credentials?",
            use_container_width=True
        ):
            st.session_state.pending_question = "How do I rotate AWS IAM credentials?"
            st.session_state.view = "chat"
            st.rerun()
    with col2:
        if st.button(
            "How do I fix a pod in CrashLoopBackOff?",
            use_container_width=True
        ):
            st.session_state.pending_question = "How do I fix a pod in CrashLoopBackOff?"
            st.session_state.view = "chat"
            st.rerun()
    with col3:
        if st.button(
            "How do I reduce AWS costs?",
            use_container_width=True
        ):
            st.session_state.pending_question = "How do I reduce AWS costs?"
            st.session_state.view = "chat"
            st.rerun()

    # Chat input on home screen too
    if prompt := st.chat_input("Ask about your cloud infrastructure..."):
        st.session_state.pending_question = prompt
        st.session_state.view = "chat"
        st.rerun()


# ── CHAT VIEW ─────────────────────────────────────────────────────────────────
elif st.session_state.view == "chat":
    st.title("RAG Cloud Docs")

    # Handle pending question — fires when arriving from home or history buttons
    if st.session_state.pending_question:
        prompt = st.session_state.pending_question
        st.session_state.pending_question = None

        st.session_state.messages = [{"role": "user", "content": prompt}]

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                result = ask_question(prompt)
                if result:
                    answer, sources, chunks_used, model = render_answer(result)

                    # Save to messages and history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "chunks_used": chunks_used,
                        "model": model,
                    })
                    st.session_state.chat_sessions.append({
                        "question": prompt,
                        "answer": answer,
                        "sources": sources,
                        "chunks_used": chunks_used,
                        "model": model,
                    })

    else:
        # Render existing messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("sources"):
                    with st.expander("Sources"):
                        for source in message["sources"]:
                            st.caption(f"📄 {source}")
                if message.get("chunks_used"):
                    st.caption(
                        f"Chunks used: {message['chunks_used']} · "
                        f"Model: {message.get('model', 'unknown')}"
                    )

    # Chat input — follow-up questions
    if prompt := st.chat_input("Ask a follow-up question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                result = ask_question(prompt)
                if result:
                    answer, sources, chunks_used, model = render_answer(result)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "chunks_used": chunks_used,
                        "model": model,
                    })
                    st.session_state.chat_sessions.append({
                        "question": prompt,
                        "answer": answer,
                        "sources": sources,
                        "chunks_used": chunks_used,
                        "model": model,
                    })