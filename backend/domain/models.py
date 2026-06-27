from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Note:
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    folder: str = ""
    filename: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_content(self, new_content: str) -> None:
        self.content = new_content
        self.updated_at = datetime.now()

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

@dataclass
class Personality:
    interactions_count: int = 0
    user_traits: list[str] = field(default_factory=list)
    favorite_topics: list[str] = field(default_factory=list)
    language_preference: str = "es"
    catchphrases: list[str] = field(default_factory=list)
    memory: list[str] = field(default_factory=list)
    last_topics: list[str] = field(default_factory=list)

    def record_interaction(self) -> None:
        self.interactions_count += 1

    def add_trait(self, trait: str) -> None:
        if trait not in self.user_traits:
            self.user_traits.append(trait)
            self.user_traits = self.user_traits[-20:]  # keep last 20

    def add_topic(self, topic: str) -> None:
        if topic not in self.favorite_topics:
            self.favorite_topics.append(topic)
            self.favorite_topics = self.favorite_topics[-10:]

@dataclass
class Connection:
    source_id: str
    target_id: str
    strength: float = 0.0
    common_terms: list[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=datetime.now)

@dataclass
class QuizQuestion:
    number: int
    question: str
    options: list[str]  # [A, B, C, D]
    correct_answer: str  # "A", "B", "C", or "D"

@dataclass
class Quiz:
    topic: str
    questions: list[QuizQuestion]
    total_count: int
    generated_at: datetime = field(default_factory=datetime.now)
    language: str = "es"

    def to_markdown(self) -> str:
        lines = [f"# Quiz: {self.topic}", f"", f"**Total: {self.total_count} preguntas**", f"", "---", f""]
        for q in self.questions:
            lines.append(f"{q.number}. {q.question}")
            labels = ["A", "B", "C", "D"]
            for i, opt in enumerate(q.options):
                lines.append(f"   {labels[i]}) {opt}")
            lines.append(f"")
        lines.append("---")
        lines.append("## Respuestas Correctas")
        for q in self.questions:
            lines.append(f"{q.number}. {q.correct_answer}")
        return "\n".join(lines)

    @property
    def question_count(self) -> int:
        return len(self.questions)
