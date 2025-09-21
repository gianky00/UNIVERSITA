import tkinter as tk
from pathlib import Path
from typing import List, Dict, Optional, Any

class Question:
    """Rappresenta una singola domanda del quiz."""
    def __init__(self, number: str, text: str, options: List[str], correct_answer: Optional[str], image_path: Optional[Path] = None):
        self.id = text.strip()
        self.number = number
        self.text = text
        self.options = options
        self.correct_answer = correct_answer
        self.image_path = image_path
        self.user_answer = tk.StringVar(value="")
        self.time_taken = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number, "text": self.text, "options": self.options,
            "image_path": str(self.image_path) if self.image_path else None,
            "correct_answer": self.correct_answer
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        image_path = Path(data["image_path"]) if data["image_path"] and data["image_path"] != "None" else None
        return cls(data["number"], data["text"], data["options"], data["correct_answer"], image_path)
