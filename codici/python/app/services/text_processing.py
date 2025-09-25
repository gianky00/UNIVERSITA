import re
import math
import collections
from pathlib import Path
from typing import List, Dict, Set

from app.models.question_model import Question

class TextFileParser:
    BOOKMARK = "---SEGNALIBRO_STUDIO---"
    def __init__(self, file_path: Path): self.file_path = file_path
    def parse(self) -> List[Question]:
        questions: List[Question] = []
        question_counter = 1
        try:
            content = self.file_path.read_text(encoding='utf-8')
        except Exception:
            return []

        if self.BOOKMARK in content:
            content, _ = content.split(self.BOOKMARK, 1)

        # Split the content by lines starting with #, which indicates a new question
        blocks = re.split(r'^\s*#\s*', content, flags=re.MULTILINE)
        for block in filter(None, (b.strip() for b in blocks)):
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines:
                continue

            q_text_full = lines.pop(0)
            # Assign a unique sequential ID to each question, ignoring the number in the file
            # to prevent issues with duplicate question numbers.
            q_number = str(question_counter)

            options, correct_answer, image_path = [], None, None
            for line in lines:
                if line.startswith('[image:'):
                    image_path = Path(line.replace('[image:', '').replace(']', '').strip())
                elif line.startswith('*'):
                    option_text = line[1:].strip()
                    options.append(option_text)
                    correct_answer = option_text
                else:
                    options.append(line)

            if options:
                questions.append(Question(q_number, q_text_full, options, correct_answer, image_path))
                question_counter += 1
        return questions

class SimilarityAnalyser:
    ITALIAN_STOP_WORDS = set(['a', 'adesso', 'ai', 'al', 'alla', 'allo', 'allora', 'altre', 'altri', 'altro', 'anche', 'ancora', 'avere', 'aveva', 'avevano', 'c', 'che', 'chi', 'ci', 'come', 'con', 'contro', 'cui', 'da', 'dagli', 'dai', 'dal', 'dall', 'dalla', 'dalle', 'dallo', 'de', 'degli', 'dei', 'del', 'dell', 'della', 'delle', 'dello', 'dentro', 'di', 'dov', 'dove', 'e', 'ed', 'era', 'erano', 'essere', 'fa', 'fino', 'fra', 'fu', 'furono', 'gli', 'ha', 'hanno', 'hai', 'ho', 'i', 'il', 'in', 'io', 'la', 'le', 'lei', 'li', 'lo', 'loro', 'lui', 'ma', 'me', 'mi', 'mia', 'mie', 'miei', 'mio', 'ne', 'negli', 'nei', 'nel', 'nell', 'nella', 'nelle', 'nello', 'noi', 'non', 'nostra', 'nostre', 'nostri', 'nostro', 'o', 'ogni', 'per', 'perche', 'perché', 'piu', 'più', 'quale', 'quando', 'quanta', 'quante', 'quanti', 'quanto', 'quella', 'quelle', 'quelli', 'quello', 'questa', 'queste', 'questi', 'questo', 're', 'se', 'sei', 'senza', 'si', 'sia', 'siamo', 'siete', 'sono', 'sta', 'stata', 'state', 'stati', 'stato', 'su', 'sua', 'sue', 'sui', 'suo', 'tra', 'tu', 'tua', 'tue', 'tui', 'tuo', 'un', 'una', 'uno', 'vi', 'voi', 'vostra', 'vostre', 'vostri', 'vostro'])
    SIMILARITY_THRESHOLD = 0.35

    def __init__(self, questions: List[Question]):
        self.questions = questions
        self.question_map = {q.id: q for q in questions}

    def _preprocess(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        return [word for word in words if word not in self.ITALIAN_STOP_WORDS]

    def _calculate_cosine_similarity(self, vec1: Dict, vec2: Dict) -> float:
        intersection = set(vec1.keys()) & set(vec2.keys())
        dot_product = sum(vec1[x] * vec2[x] for x in intersection)
        sum_sq_vec1 = sum(val**2 for val in vec1.values())
        sum_sq_vec2 = sum(val**2 for val in vec2.values())
        magnitude = math.sqrt(sum_sq_vec1) * math.sqrt(sum_sq_vec2)
        return dot_product / magnitude if magnitude != 0 else 0

    def compute_similarity_map(self) -> Dict[str, List[str]]:
        docs = {q.id: self._preprocess(q.text + " " + " ".join(q.options)) for q in self.questions}
        vocab = set(word for words in docs.values() for word in words)
        if not vocab: return {}
        num_docs = len(docs)
        idf = {word: math.log(num_docs / (1 + sum(1 for doc_words in docs.values() if word in doc_words))) for word in vocab}

        tfidf_vectors = {}
        for doc_id, words in docs.items():
            term_counts = collections.Counter(words)
            total_terms = len(words)
            if total_terms == 0: continue
            vector = {word: (count / total_terms) * idf[word] for word, count in term_counts.items()}
            tfidf_vectors[doc_id] = vector

        similarity_map = collections.defaultdict(list)
        question_ids = list(self.question_map.keys())
        for i in range(len(question_ids)):
            for j in range(i + 1, len(question_ids)):
                id1, id2 = question_ids[i], question_ids[j]
                if id1 in tfidf_vectors and id2 in tfidf_vectors:
                    sim = self._calculate_cosine_similarity(tfidf_vectors[id1], tfidf_vectors[id2])
                    if sim > self.SIMILARITY_THRESHOLD:
                        similarity_map[id1].append(id2)
                        similarity_map[id2].append(id1)
        return {k: list(v) for k, v in similarity_map.items()} # Convert back to dict for JSON
