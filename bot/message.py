def build_word_of_the_day_message(word: str, word_content: dict[str, str]) -> str:
    """Create the text of the post.

    Args:
        word (str): Word of the day.
        word_content (dict[str, str]): Word details parsed from the API response.

    Returns:
        str: Post text.
    """
    lines = [
        f"🌟 Word of the day: {word}",
        f"📚 Part of Speech: {word_content['pos']}",
    ]
    pronunciation = word_content.get("pronunciation")
    if pronunciation:
        lines.append(f"🔊 Pronunciation: {pronunciation}")
    lines.append(f"📖 Definition: {word_content['definition']}")
    return "\n".join(lines)
