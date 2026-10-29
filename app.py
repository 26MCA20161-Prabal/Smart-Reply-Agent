import os
from datetime import datetime

import streamlit as st

from llm import PROVIDERS, LLMError, generate_replies, refine_reply

st.set_page_config(page_title="Smart Reply Assistant", page_icon="✉️", layout="wide")

TONES = ["Friendly", "Formal", "Firm", "Apologetic", "Enthusiastic", "Empathetic"]
LENGTHS = ["Short", "Medium", "Detailed"]
LANGUAGES = ["English", "Hindi", "Punjabi", "Hinglish"]

EXAMPLES = {
    "Pick an example...": "",
    "Late assignment (to a teacher)": "Hi, I noticed your assignment was submitted 2 days after the deadline. Please explain the reason for the delay.",
    "Client complaint": "I ordered a product last week and it arrived damaged. This is the second time this has happened. I want a refund immediately.",
    "Event invitation": "We are hosting a small get-together this Saturday at 6 pm at our place. Would love for you to join us!",
    "Job interview follow-up": "Thank you for attending the interview. Could you let us know your expected joining date and salary expectations?",
}

# ---------- session state ----------
st.session_state.setdefault("results", None)
st.session_state.setdefault("history", [])
st.session_state.setdefault("last_message", "")


def get_secret(name):
    """Read a key from Streamlit secrets or environment variables."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, "")


# ---------- sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    provider = st.selectbox(
        "AI provider",
        PROVIDERS,
        index=0,
        help="Demo needs no key. Gemini has a free tier. Claude needs an Anthropic API key.",
    )
    api_key = ""
    if provider != "Demo":
        env_name = "GEMINI_API_KEY" if provider == "Gemini" else "ANTHROPIC_API_KEY"
        api_key = get_secret(env_name)
        if api_key:
            st.success(f"Using {env_name} from your environment.")
        else:
            api_key = st.text_input(f"{provider} API key", type="password")
            st.caption("Your key stays in this session and is never saved to disk.")

    st.divider()
    language = st.selectbox("Reply language", LANGUAGES)
    n_variations = st.slider("Number of variations", 1, 3, 2)

    st.divider()
    st.subheader("🕘 History")
    if st.session_state.history:
        for item in reversed(st.session_state.history[-8:]):
            with st.expander(f"{item['time']} · {item['tone']}"):
                st.caption("Received:")
                st.write(item["message"][:200] + ("…" if len(item["message"]) > 200 else ""))
                st.caption("Reply:")
                st.code(item["reply"], language=None)
        if st.button("Clear history"):
            st.session_state.history = []
            st.rerun()
    else:
        st.caption("Your generated replies will appear here.")

# ---------- main ----------
st.title("✉️ Smart Reply Assistant")
st.caption("Paste a message, choose a tone, and get ready-to-send reply drafts.")

example = st.selectbox("Try an example", list(EXAMPLES.keys()))
default_text = EXAMPLES[example] or st.session_state.last_message
message = st.text_area("Message you received", value=default_text, height=160, placeholder="Paste the email or message here…")

col1, col2 = st.columns(2)
with col1:
    tone = st.radio("Tone", TONES, horizontal=True)
with col2:
    length = st.radio("Length", LENGTHS, horizontal=True, index=1)

extra = st.text_input("Anything specific to include? (optional)", placeholder="e.g. mention I'm free on Friday")

if st.button("Generate replies", type="primary", use_container_width=True):
    st.session_state.last_message = message
    try:
        with st.spinner("Writing your replies…"):
            st.session_state.results = generate_replies(
                message, tone, length, language, n_variations, extra, provider, api_key
            )
            st.session_state.results["tone"] = tone
            st.session_state.results["message"] = message
            for reply in st.session_state.results["replies"]:
                st.session_state.history.append(
                    {"time": datetime.now().strftime("%H:%M"), "tone": tone, "message": message, "reply": reply}
                )
        st.rerun()  # redraw so the sidebar history includes the new replies right away
    except LLMError as exc:
        st.session_state.results = None
        st.error(str(exc))

results = st.session_state.results
if results:
    st.divider()
    info_cols = st.columns(2)
    info_cols[0].metric("Detected message type", results["message_type"].title())
    info_cols[1].metric("Suggested tone", results["suggested_tone"] or "—")

    st.subheader("Your reply drafts")
    st.caption("Use the copy icon at the top-right of each draft.")
    tabs = st.tabs([f"Option {i + 1}" for i in range(len(results["replies"]))])
    for i, tab in enumerate(tabs):
        with tab:
            st.code(results["replies"][i], language=None, wrap_lines=True)
            instruction = st.text_input(
                "Want changes?",
                key=f"refine_{i}",
                placeholder="e.g. make it shorter, add a deadline, sound warmer",
            )
            if st.button("Revise this draft", key=f"revise_{i}"):
                try:
                    with st.spinner("Revising…"):
                        revised = refine_reply(
                            results["message"], results["replies"][i], instruction,
                            language, provider, api_key, tone=results["tone"],
                        )
                    results["replies"][i] = revised["replies"][0]
                    st.session_state.history.append(
                        {"time": datetime.now().strftime("%H:%M"), "tone": results["tone"],
                         "message": results["message"], "reply": revised["replies"][0]}
                    )
                    st.rerun()
                except LLMError as exc:
                    st.error(str(exc))

st.divider()
st.caption("AI-generated drafts can contain mistakes. Always review before sending.")
