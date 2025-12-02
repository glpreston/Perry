import uuid
from memory import MemoryDB


def test_save_and_load_qa_and_group():
    db = MemoryDB()
    test_agent = f"test_agent_{uuid.uuid4().hex[:8]}"
    group_key = "__group__"

    # ensure a clean slate
    try:
        db.clear_memory(test_agent)
    except Exception:
        pass
    try:
        db.clear_memory(group_key)
    except Exception:
        pass

    try:
        # save a QA pair for the agent
        q_text = "Q: How are you?"
        a_text = "A: I'm fine, thanks."
        db.save_qa(test_agent, q_text, a_text)

        # load recent QA for the agent and assert the saved pair is present
        agent_rows = db.load_recent_qa(test_agent, limit=5)
        assert agent_rows, "No rows returned for agent"
        first = agent_rows[0]
        assert isinstance(first, dict)
        # memory stores question/answer under 'q' and 'a'
        assert first.get("q") == q_text
        assert first.get("a") == a_text

        # save a group (broadcast) question-only entry
        gq = "Anyone here?"
        db.save_qa(group_key, gq, "")

        # load recent group QA and assert the question-only entry exists
        group_rows = db.load_recent_qa(None, limit=5)  # None => group
        assert any(r.get("q") == gq for r in group_rows), "Group question not found"

    finally:
        # cleanup
        try:
            db.clear_memory(test_agent)
        except Exception:
            pass
        try:
            db.clear_memory(group_key)
        except Exception:
            pass
