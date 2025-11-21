from models import SessionState


def test_rollup_history_and_slots():
    state = SessionState(session_id="demo")
    for i in range(10):
        state.add_user(f"user turn {i}")
        state.add_assistant(f"bot turn {i}")
    state.rollup_history(keep_last=4)
    assert len(state.history) == 4
    assert "user turn 0" in state.summary

    state.update_slot("budget", "1200")
    state.update_slot("category", "gaming")
    snapshot = state.slot_snapshot()
    assert "budget=1200" in snapshot
    assert "category=gaming" in snapshot
