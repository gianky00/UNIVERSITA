import datetime
from typing import Dict, Any, Optional

from .question_model import Question

class SRSItem:
    """Rappresenta una domanda nel sistema SRS, con i suoi metadati di studio."""
    def __init__(self, question: Question, srs_level: int = 0, next_review_date: Optional[datetime.date] = None, lapses: int = 0):
        self.question = question
        self.srs_level = srs_level
        self.next_review_date = next_review_date or (datetime.date.today() + datetime.timedelta(days=1))
        self.lapses = lapses

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question.to_dict(), "srs_level": self.srs_level,
            "next_review_date": self.next_review_date.isoformat(), "lapses": self.lapses
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SRSItem':
        question = Question.from_dict(data["question"])
        return cls(question, data["srs_level"], datetime.date.fromisoformat(data["next_review_date"]), data.get("lapses", 0))
