class DomainError(Exception):
    """Base domain exception."""
    pass

class NoteNotFoundError(DomainError):
    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"Note not found: {filename}")

class PersonalityNotFoundError(DomainError):
    def __init__(self):
        super().__init__("Personality state not found")

class QuizGenerationError(DomainError):
    def __init__(self, topic: str, reason: str = ""):
        self.topic = topic
        super().__init__(f"Failed to generate quiz for '{topic}': {reason}")

class SearchIndexError(DomainError):
    def __init__(self, reason: str = ""):
        super().__init__(f"Search index error: {reason}")

class LLMProviderError(DomainError):
    def __init__(self, provider: str, reason: str = ""):
        self.provider = provider
        super().__init__(f"LLM provider '{provider}' error: {reason}")
