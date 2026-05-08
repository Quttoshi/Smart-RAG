def validate_text(text: str):
    if not text or not text.strip():
        raise ValueError("Text content cannot be empty")
