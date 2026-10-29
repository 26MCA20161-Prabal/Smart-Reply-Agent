"""LLM backend for the Smart Reply Assistant.

Supports three providers:
  - "Demo"   : no API key needed, returns canned replies (for testing / offline demos)
  - "Gemini" : Google Gemini (has a free tier) via the google-genai package
  - "Claude" : Anthropic Claude via the anthropic package
"""

import json
import os
import re

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

PROVIDERS = ["Demo", "Gemini", "Claude"]

SYSTEM_PROMPT = (
    "You are an expert writing assistant that drafts replies to emails and messages. "
    "You write clear, natural replies that match the requested tone, length and language. "
    "Never invent facts, names, dates or commitments that are not in the original message "
    "or the user's instructions; use placeholders like [your name] or [date] when details are missing. "
    "Respond ONLY with valid JSON, no markdown fences, no extra commentary."
)

LENGTH_GUIDE = {
    "Short": "2-3 sentences",
    "Medium": "one short paragraph or two",
    "Detailed": "3-4 short paragraphs with full context",
}


class LLMError(Exception):
    """Raised for any user-facing problem (missing key, bad response, API failure)."""


def build_reply_prompt(message, tone, length, language, n_variations, extra=""):
    extra_line = f"\nExtra instructions from the user: {extra.strip()}" if extra.strip() else ""
    return f"""Here is a message I received:
\"\"\"
{message.strip()}
\"\"\"

Write {n_variations} different reply drafts to it.
- Tone: {tone}
- Length: {LENGTH_GUIDE.get(length, length)}
- Language: {language}
- Each draft should take a slightly different approach (wording or structure), not just rephrase.
- Include a greeting and sign-off where appropriate for an email; keep chat messages casual if the original is casual.{extra_line}

Also classify the incoming message.

Return JSON in exactly this shape:
{{
  "message_type": "one of: complaint, request, invitation, question, follow-up, thanks, other",
  "suggested_tone": "the tone you would recommend for this message, in 1-3 words",
  "replies": ["draft 1", "draft 2"]
}}"""


def build_refine_prompt(original_message, current_reply, instruction, language):
    return f"""Original message I received:
\"\"\"
{original_message.strip()}
\"\"\"

Current draft reply:
\"\"\"
{current_reply.strip()}
\"\"\"

Revise the draft following this instruction: {instruction.strip()}
Keep the language as {language}.

Return JSON in exactly this shape:
{{
  "replies": ["the revised reply"]
}}"""


def parse_json_response(text):
    """Parse model output into a dict, tolerating code fences or stray text."""
    if not text:
        raise LLMError("The model returned an empty response. Please try again.")
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise LLMError("Could not read the model's response. Please try again.")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise LLMError("Could not read the model's response. Please try again.")
    replies = data.get("replies")
    if isinstance(replies, str):
        replies = [replies]
    if not isinstance(replies, list) or not replies:
        raise LLMError("The model did not return any reply drafts. Please try again.")
    return {
        "message_type": str(data.get("message_type", "other")).strip().lower(),
        "suggested_tone": str(data.get("suggested_tone", "")).strip(),
        "replies": [str(r).strip() for r in replies if str(r).strip()],
    }


def _call_gemini(prompt, api_key):
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise LLMError("The 'google-genai' package is not installed. Run: pip install -r requirements.txt")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.8,
            ),
        )
        return response.text
    except Exception as exc:  # network, quota, invalid key...
        raise LLMError(f"Gemini request failed: {exc}")


def _call_claude(prompt, api_key):
    try:
        import anthropic
    except ImportError:
        raise LLMError("The 'anthropic' package is not installed. Run: pip install -r requirements.txt")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            temperature=0.8,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    except Exception as exc:
        raise LLMError(f"Claude request failed: {exc}")


def _demo_replies(tone, n_variations, refine=False):
    samples = {
        "Formal": "Dear [Name],\n\nThank you for your message. I have reviewed the details and will get back to you with a complete response by [date].\n\nKind regards,\n[Your name]",
        "Friendly": "Hi [Name]!\n\nThanks so much for reaching out. I'll take a look and get back to you by [date]. Let me know if anything changes!\n\nCheers,\n[Your name]",
        "Firm": "Hello [Name],\n\nI have received your message. To move forward, I need the requested details by [date]. Please confirm this works for you.\n\nRegards,\n[Your name]",
        "Apologetic": "Hi [Name],\n\nI'm sorry for the delay and any inconvenience caused. I'm working on it now and will update you by [date].\n\nSincerely,\n[Your name]",
    }
    base = samples.get(tone, samples["Friendly"])
    if refine:
        return {"message_type": "other", "suggested_tone": tone, "replies": [base + "\n\n(Demo mode: this is a sample revision.)"]}
    replies = [f"{base}\n\n(Demo mode sample {i + 1}: add an API key for real, personalised replies.)" for i in range(n_variations)]
    return {"message_type": "request", "suggested_tone": "Friendly", "replies": replies}


def _run(prompt, provider, api_key):
    if provider == "Gemini":
        if not api_key:
            raise LLMError("Please add your Gemini API key in the sidebar.")
        return parse_json_response(_call_gemini(prompt, api_key))
    if provider == "Claude":
        if not api_key:
            raise LLMError("Please add your Anthropic API key in the sidebar.")
        return parse_json_response(_call_claude(prompt, api_key))
    raise LLMError(f"Unknown provider: {provider}")


def generate_replies(message, tone, length, language, n_variations, extra, provider, api_key):
    if not message or not message.strip():
        raise LLMError("Please paste the message you want to reply to.")
    if provider == "Demo":
        return _demo_replies(tone, n_variations)
    prompt = build_reply_prompt(message, tone, length, language, n_variations, extra)
    return _run(prompt, provider, api_key)


def refine_reply(original_message, current_reply, instruction, language, provider, api_key, tone="Friendly"):
    if not instruction or not instruction.strip():
        raise LLMError("Please type how you want the reply changed (e.g. 'make it shorter').")
    if provider == "Demo":
        return _demo_replies(tone, 1, refine=True)
    prompt = build_refine_prompt(original_message, current_reply, instruction, language)
    return _run(prompt, provider, api_key)
