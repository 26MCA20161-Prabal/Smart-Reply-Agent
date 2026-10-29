"""Quick tests that need no API key. Run: python test_llm.py"""

from llm import LLMError, generate_replies, parse_json_response, refine_reply


def test_parse_plain_json():
    out = parse_json_response('{"message_type": "Request", "suggested_tone": "Formal", "replies": ["Hi"]}')
    assert out["replies"] == ["Hi"] and out["message_type"] == "request"


def test_parse_fenced_json():
    out = parse_json_response('```json\n{"replies": ["A", "B"]}\n```')
    assert out["replies"] == ["A", "B"]


def test_parse_with_stray_text():
    out = parse_json_response('Sure! Here you go: {"replies": ["Hello"]} Hope that helps.')
    assert out["replies"] == ["Hello"]


def test_parse_bad_input():
    for bad in ["", "not json at all", '{"replies": []}']:
        try:
            parse_json_response(bad)
        except LLMError:
            continue
        raise AssertionError(f"expected LLMError for {bad!r}")


def test_demo_generate_and_refine():
    out = generate_replies("Hello there", "Formal", "Short", "English", 3, "", "Demo", "")
    assert len(out["replies"]) == 3
    rev = refine_reply("Hello there", out["replies"][0], "shorter", "English", "Demo", "")
    assert len(rev["replies"]) == 1


def test_validation_errors():
    for call in (
        lambda: generate_replies("  ", "Formal", "Short", "English", 1, "", "Demo", ""),
        lambda: generate_replies("Hi", "Formal", "Short", "English", 1, "", "Gemini", ""),
        lambda: refine_reply("Hi", "Reply", "", "English", "Demo", ""),
    ):
        try:
            call()
        except LLMError:
            continue
        raise AssertionError("expected LLMError")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
    print("All tests passed.")
