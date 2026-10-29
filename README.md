# ✉️ Smart Reply Assistant

An AI-powered web app that drafts replies to emails and messages. Paste a message, pick a tone, length and language, and get multiple ready-to-send drafts. Built with Python, Streamlit and an LLM API (Google Gemini or Anthropic Claude).

## Features

- Tone selector: Friendly, Formal, Firm, Apologetic, Enthusiastic, Empathetic
- Length control: Short, Medium, Detailed
- Languages: English, Hindi, Punjabi, Hinglish
- 1-3 reply variations per request
- Auto-detects the message type (complaint, request, invitation...) and suggests a tone
- "Revise this draft" box (e.g. "make it shorter", "add a deadline")
- One-click copy button on every draft
- History panel for the current session
- Demo mode that works with no API key

## Project structure

```
app.py            Streamlit user interface
llm.py            Prompt building, API calls (Gemini / Claude / Demo), JSON parsing
test_llm.py       Tests that run without an API key
requirements.txt  Python dependencies
.env.example      Template for API keys
```

## Run it locally

1. Install Python 3.10 or newer.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. (Optional) Set an API key. Get a free Gemini key at https://aistudio.google.com/apikey
   - Windows (PowerShell): `$env:GEMINI_API_KEY="your_key"`
   - Mac/Linux: `export GEMINI_API_KEY="your_key"`
   You can also skip this and paste the key into the app's sidebar, or use **Demo** mode.
4. Start the app:
   ```
   streamlit run app.py
   ```
5. Open http://localhost:8501

## Run the tests

```
python test_llm.py
```

## Deploy for free (Streamlit Community Cloud)

1. Push this folder to a public GitHub repository (`.env` is already git-ignored, so your key is not uploaded).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, choose your repo, and set the main file to `app.py`.
4. Under **Advanced settings → Secrets**, add:
   ```
   GEMINI_API_KEY = "your_key"
   ```
5. Click **Deploy**. You get a public link you can share in your presentation.

## How it works

1. The user's message, tone, length, language and extra notes are turned into a structured prompt (`build_reply_prompt` in `llm.py`).
2. A system prompt tells the model to stay faithful to the message and use placeholders like `[date]` instead of inventing details.
3. The model is asked to return JSON containing the message type, a suggested tone and the reply drafts.
4. The app parses that JSON (tolerating code fences or stray text) and displays each draft in its own tab.
5. The revise feature sends the original message, the current draft and the change request back to the model.

## Limitations

- Drafts can contain mistakes or miss context; always review before sending.
- Quality in Hindi and Punjabi may be lower than in English.
- Free API tiers have rate limits.
- History is stored only for the current browser session.

## Possible future improvements

- Voice input and read-aloud output
- Gmail integration to read and send directly
- Saved custom tones (e.g. "my own writing style")
- Export history to a file
