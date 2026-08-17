from bot.message import BLUESKY_MAX_LENGTH, build_word_of_the_day_message


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


def test_long_definition_is_trimmed_to_the_limit():
    # The real definition that made the 2026-08-16 run fail at 371 graphemes
    definition = (
        "the use of a word to modify or govern two or more words usually in such "
        "a manner that it applies to each word in a different sense (as "
        '"opened" in "opened the door and her heart to the stray kitten") or '
        'makes sense with only one word (as "rolling" in "rolling lightning and '
        'thunder")'
    )
    message = build_word_of_the_day_message(
        "zeugma",
        {"pos": "noun", "pronunciation": "ˈzüg-mə", "definition": definition},
    )

    assert len(message) <= BLUESKY_MAX_LENGTH
    assert message.endswith("…")
    # The word, part of speech and pronunciation survive intact
    assert message.startswith(
        "🌟 Word of the day: zeugma\n📚 Part of Speech: noun\n🔊 Pronunciation: ˈzüg-mə\n"
    )


def test_short_definition_is_left_alone():
    message = build_word_of_the_day_message(
        "rapport", {"pos": "noun", "definition": "a friendly relationship"}
    )
    assert "…" not in message


def test_trimming_stops_at_a_word_boundary():
    message = build_word_of_the_day_message(
        "verbose", {"pos": "adjective", "definition": "wordy " * 100}
    )
    assert len(message) <= BLUESKY_MAX_LENGTH
    assert message.endswith("wordy…")
