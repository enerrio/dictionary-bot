import datetime

from bot import schedule


class DummyInstant:
    """Stand-in for whenever.Instant pinned to a fixed moment."""

    @staticmethod
    def now():
        class DummyTZ:
            def to_tz(self, tz):
                return self

            def py_datetime(self):
                return datetime.datetime(2026, 8, 10, 9, 0)

        return DummyTZ()


def test_already_posted_today_missing_state_file(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "Instant", DummyInstant)
    assert schedule.already_posted_today(tmp_path / "last_posted_date") is False


def test_record_post_then_already_posted(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "Instant", DummyInstant)
    state_file = tmp_path / "state" / "last_posted_date"

    schedule.record_post(state_file)

    assert state_file.read_text().strip() == "2026-08-10"
    assert schedule.already_posted_today(state_file) is True


def test_already_posted_today_stale_state(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "Instant", DummyInstant)
    state_file = tmp_path / "last_posted_date"
    state_file.write_text("2026-08-09\n")

    assert schedule.already_posted_today(state_file) is False
