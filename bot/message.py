import logging

logger = logging.getLogger(__name__)

# Bluesky rejects a post longer than 300 graphemes. Python counts code points
# rather than graphemes, but a code point count is never lower than the grapheme
# count, so measuring with len() stays inside the limit.
BLUESKY_MAX_LENGTH = 300


def _truncate(text: str, limit: int) -> str:
    """Shorten text to fit a character budget, ending at a word boundary.

    Args:
        text (str): Text to shorten.
        limit (int): Maximum length of the result, including the ellipsis.

    Returns:
        str: The text, shortened only if it exceeded the budget.
    """
    if len(text) <= limit:
        return text
    if limit <= 1:
        return "…"[:limit]
    trimmed = text[: limit - 1].rstrip()
    last_space = trimmed.rfind(" ")
    if last_space > 0:
        trimmed = trimmed[:last_space].rstrip()
    return f"{trimmed}…"


def build_word_of_the_day_message(word: str, word_content: dict[str, str]) -> str:
    """Create the text of the post.

    Args:
        word (str): Word of the day.
        word_content (dict[str, str]): Word details parsed from the API response.

    Returns:
        str: Post text, trimmed to Bluesky's length limit.
    """
    lines = [
        f"🌟 Word of the day: {word}",
        f"📚 Part of Speech: {word_content['pos']}",
    ]
    pronunciation = word_content.get("pronunciation")
    if pronunciation:
        lines.append(f"🔊 Pronunciation: {pronunciation}")

    # Definitions are the only part that runs long, so spend the leftover
    # budget on them rather than dropping the word or its pronunciation
    prefix = "📖 Definition: "
    header_length = len("\n".join(lines)) + len("\n") + len(prefix)
    definition = word_content["definition"]
    trimmed = _truncate(definition, BLUESKY_MAX_LENGTH - header_length)
    if trimmed != definition:
        logger.info(
            "Definition trimmed from %d to %d characters to fit Bluesky's limit",
            len(definition),
            len(trimmed),
        )
    lines.append(f"{prefix}{trimmed}")
    return "\n".join(lines)
