import pytest


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test_api_key")
    monkeypatch.setenv("BLUESKY_USERNAME", "test_username")
    monkeypatch.setenv("BLUESKY_PASSWORD", "test_password")
    monkeypatch.setenv("DEBUG", "true")


@pytest.fixture
def api_response():
    """A trimmed-down Merriam-Webster collegiate API response."""
    return [
        {
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
            "quotes": [{"t": "They had an easy {it}rapport{/it}."}],
        }
    ]
