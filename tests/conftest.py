import pytest


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test_api_key")
    monkeypatch.setenv("BLUESKY_USERNAME", "test_username")
    monkeypatch.setenv("BLUESKY_PASSWORD", "test_password")
    monkeypatch.setenv("DEBUG", "true")


def make_entry(entry_id, fl, definition, pronunciations=None):
    """Build a trimmed-down entry in the shape the collegiate API returns."""
    entry = {
        "meta": {"id": entry_id},
        "fl": fl,
        "hwi": {"hw": entry_id.split(":")[0]},
        "def": [{"sseq": [[["sense", {"dt": [["text", definition]]}]]]}],
    }
    if pronunciations is not None:
        entry["hwi"]["prs"] = pronunciations
    return entry


@pytest.fixture
def homograph_response():
    """Two homographs of the same headword, plus a phrase that contains it.

    Mirrors the real response for "dudgeon", where the archaic sense sorts
    first and the word of the day is the second homograph.
    """
    return [
        make_entry("dudgeon:1", "noun", "{bc}a wood used especially for dagger hilts"),
        make_entry("dudgeon:2", "noun", "{bc}a fit or state of indignation "),
        make_entry("in high dudgeon", "phrase", "{bc}feeling angry or offended "),
    ]


@pytest.fixture
def api_response():
    """A trimmed-down Merriam-Webster collegiate API response."""
    return [
        {
            "meta": {"id": "rapport"},
            "fl": "noun",
            "hwi": {
                "hw": "rap*port",
                "prs": [
                    {"mw": "ra-ˈpȯr", "sound": {"audio": "rappor01"}},
                    {"mw": "rə-ˈpȯr"},
                ],
            },
            "def": [
                {
                    "sseq": [
                        [
                            [
                                "sense",
                                {
                                    "dt": [
                                        [
                                            "text",
                                            "{bc}a friendly, harmonious {a_link|relationship}",
                                        ]
                                    ]
                                },
                            ]
                        ]
                    ]
                }
            ],
        }
    ]
