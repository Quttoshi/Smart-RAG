def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

    return text
