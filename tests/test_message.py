from bot.message import build_word_of_the_day_message


def test_build_message():
    message = build_word_of_the_day_message(
        "rapport",
        {
            "pos": "noun",
            "pronunciation": "ra-ˈpȯr",
            "definition": "a friendly, harmonious relationship",
        },
    )
    assert message == (
        "🌟 Word of the day: rapport\n"
        "📚 Part of Speech: noun\n"
        "🔊 Pronunciation: ra-ˈpȯr\n"
        "📖 Definition: a friendly, harmonious relationship"
    )


def test_build_message_without_pronunciation():
    message = build_word_of_the_day_message(
        "rapport", {"pos": "noun", "definition": "a friendly relationship"}
    )
    assert "Pronunciation" not in message
    assert message.endswith("📖 Definition: a friendly relationship")
