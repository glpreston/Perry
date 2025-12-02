import uuid
from memory import MemoryDB


def is_error_text(s: str) -> bool:
    if not s:
        return False
    low = s.lower()
    return (low.startswith("(error") or "timed out" in low or "request error" in low or "timeout" in low)


def test_memory_filtering_flow():
    db = MemoryDB()
    agent = f"test_agent_{uuid.uuid4().hex[:8]}"

    # Ensure no pre-existing rows for this agent
    try:
        db.clear_memory(agent)
    except Exception:
        pass

    # Insert a mix of good and error/timeout answers
    db.save_qa(agent, "Q1", "This is a good answer")
    db.save_qa(agent, "Q2", "(Timed out — server too slow)")
    db.save_qa(agent, "Q3", "Request Error: connection refused")
    db.save_qa(agent, "Q4", "")

    # Load and apply the same filtering heuristic used in the app
    rows = db.load_recent_qa(agent, limit=10)
    filtered = [r for r in rows if r.get('a') and not is_error_text(r.get('a'))]

    # We expect only the good answer to survive the filter
    answers = [r.get('a') for r in filtered]
    assert "This is a good answer" in answers
    assert all(not is_error_text(a) for a in answers)

    # Cleanup
    db.clear_memory(agent)
