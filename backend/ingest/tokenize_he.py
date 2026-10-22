"""Light Hebrew tokenizer for BM25: no external NLP dependency."""
import re

NIQQUD_RE = re.compile(r"[֑-ׇ]")
TOKEN_RE = re.compile(r"[א-ת]+|[a-zA-Z]+|\d+")
# Single-letter proclitics (ו, ה, ב, כ, ל, מ, ש) glued to the word: "בביטוח" -> "ביטוח".
PREFIXES = "והבכלמש"
STOPWORDS = {
    "של", "את", "על", "עם", "או", "גם", "כי", "אם", "זה", "זו", "הוא", "היא", "הם", "הן", "אני", "אתה", "את",
    "יש", "אין", "לא", "כן", "מה", "איך", "מתי", "האם", "כל", "רק", "עוד", "אל", "אשר", "כמו", "לפי", "בין",
    "אחרי", "לפני", "תוך", "כדי", "שלך", "שלי", "שלנו", "להם", "לך", "לי", "לנו", "אותו", "אותה",
}


def word_forms(text: str) -> list[set[str]]:
    """For each content word: the set of its index forms (as written, and without prefix letters)."""
    forms = []
    for tok in TOKEN_RE.findall(NIQQUD_RE.sub("", text.lower())):
        if tok in STOPWORDS:
            continue
        variants = {tok}
        stripped = tok
        for _ in range(2):
            if len(stripped) > 3 and stripped[0] in PREFIXES:
                stripped = stripped[1:]
                variants.add(stripped)
        forms.append(variants)
    return forms


def tokenize(text: str) -> list[str]:
    text = NIQQUD_RE.sub("", text.lower())
    tokens: list[str] = []
    for tok in TOKEN_RE.findall(text):
        if tok in STOPWORDS:
            continue
        tokens.append(tok)
        # Also index the form without up to two prefix letters, so "בביטוח" matches "ביטוח".
        stripped = tok
        for _ in range(2):
            if len(stripped) > 3 and stripped[0] in PREFIXES:
                stripped = stripped[1:]
                if stripped not in STOPWORDS:
                    tokens.append(stripped)
    return tokens
