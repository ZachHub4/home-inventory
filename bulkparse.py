"""Parse free-form typed or dictated text into inventory items.

Dictation is the main reason this is fuzzy. Speaking "ornaments one hundred
twelve, tree lights four" produces one long line with number words and no
punctuation you can rely on, so the parser accepts several shapes and always
feeds a preview the user confirms before anything is saved.
"""

import re

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {"hundred": 100, "thousand": 1000}
NUMBER_WORDS = set(UNITS) | set(TENS) | set(SCALES) | {"and", "a", "an"}

# Words people say before a count that aren't part of the item's name.
QTY_LEAD = {"x", "qty", "quantity", "times", "count", "of"}


def words_to_number(text):
    """Turn a run of number words into an int, or None if it isn't one."""
    tokens = re.split(r"[\s-]+", text.lower().strip())
    tokens = [t for t in tokens if t]
    if not tokens or not all(t in NUMBER_WORDS for t in tokens):
        return None
    if all(t in {"and", "a", "an"} for t in tokens):
        return None

    total = 0
    current = 0
    seen = False
    for token in tokens:
        if token in {"and"}:
            continue
        if token in {"a", "an"}:
            current += 1
            seen = True
        elif token in UNITS:
            current += UNITS[token]
            seen = True
        elif token in TENS:
            current += TENS[token]
            seen = True
        elif token == "hundred":
            current = (current or 1) * 100
            seen = True
        elif token == "thousand":
            total += (current or 1) * 1000
            current = 0
            seen = True
    return total + current if seen else None


def _clean_name(text):
    text = text.strip(" \t,;:-–—.")
    text = re.sub(r"\s+", " ", text)
    # "a wreath" / "an extension cord" - the article isn't part of the name.
    text = re.sub(r"^(?:an?)\s+", "", text, flags=re.I)
    # Drop a dangling quantity lead-in like "ornaments x" or "screws qty".
    parts = text.split()
    while parts and parts[-1].lower() in QTY_LEAD:
        parts.pop()
    text = " ".join(parts)
    return text[:1].upper() + text[1:] if text else text


def parse_line(line):
    """Return (name, quantity, description) or None if the line is empty."""
    line = line.strip()
    if not line:
        return None

    description = ""
    # "name | description" or "name -- description" splits off a description.
    for sep in ("|", " -- "):
        if sep in line:
            line, description = line.split(sep, 1)
            line, description = line.strip(), description.strip()
            break

    quantity = 1

    # Trailing digits: "Ornaments 112", "Ornaments x112", "Ornaments, 112"
    m = re.match(r"^(.*?)[\s,]*(?:x|qty|quantity|times)?[\s,]*(\d+)\s*$", line, re.I)
    if m and m.group(1).strip():
        name = _clean_name(m.group(1))
        quantity = int(m.group(2))
        return (name, max(1, quantity), description) if name else None

    # Leading digits: "112 ornaments", "4 tree lights". The name must start with
    # a non-digit, or a bare "123" splits into "3" with a quantity of 12.
    m = re.match(r"^(\d+)\s*(?:x\s*)?(\D.*)$", line, re.I)
    if m and m.group(2).strip():
        name = _clean_name(m.group(2))
        quantity = int(m.group(1))
        return (name, max(1, quantity), description) if name else None

    # Trailing number words: "ornaments one hundred twelve". Take the LONGEST
    # trailing run of number words, or "one hundred twelve" reads as just 12.
    tokens = line.split()
    start = len(tokens)
    while start > 0 and tokens[start - 1].lower() in NUMBER_WORDS:
        start -= 1
    for i in range(start, len(tokens)):
        value = words_to_number(" ".join(tokens[i:]))
        if value is not None and value > 0:
            name = _clean_name(" ".join(tokens[:i]))
            if name:
                return (name, value, description)

    # Leading number words: "twelve ornaments"
    for i in range(len(tokens), 0, -1):
        head = " ".join(tokens[:i])
        value = words_to_number(head)
        if value is not None and value > 0:
            name = _clean_name(" ".join(tokens[i:]))
            if name:
                return (name, value, description)
            break

    name = _clean_name(line)
    return (name, 1, description) if name else None


def parse_text(text):
    """Parse a block of typed or dictated text into item tuples."""
    if not text:
        return []

    lines = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        # Dictation often arrives as one run-on line; commas and semicolons are
        # the only separators available, but a comma may also precede a count
        # ("ornaments, 112"), so only split where a real item seems to follow.
        if "\n" not in raw and ("," in raw or ";" in raw):
            chunks = re.split(r"[;,]", raw)
            merged = []
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                bare_count = re.fullmatch(r"(?:x|qty)?\s*\d+", chunk, re.I) or (
                    words_to_number(chunk) is not None
                )
                if bare_count and merged:
                    merged[-1] = f"{merged[-1]} {chunk}"
                else:
                    merged.append(chunk)
            lines.extend(merged)
        else:
            lines.append(raw)

    items = []
    for line in lines:
        parsed = parse_line(line)
        if parsed:
            items.append(parsed)
    return items
