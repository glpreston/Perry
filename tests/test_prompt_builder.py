from prompt_builder import PromptBuilder


def test_strip_leading_agent_name():
    assert (
        PromptBuilder.strip_leading_agent_name("Netty: how are you?") == "how are you?"
    )
    assert PromptBuilder.strip_leading_agent_name("Rex - play!") == "play!"


def test_format_memories_and_error_filtering():
    mems = [
        {"q": "Netty: name?", "a": "I am Netty."},
        {"q": "Old: broken", "a": "(Error) request failed"},
    ]
    formatted = PromptBuilder.format_memories(mems, limit=5)
    assert any("I am Netty." in s for s in formatted)
    # error entry should still be present in format but is_error_text should flag it
    assert PromptBuilder.is_error_text("(Error) request failed")
