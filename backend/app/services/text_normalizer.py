"""Chuẩn hóa text CV sau khi trích xuất từ PDF (thường bị dính chữ, xuống dòng sai)."""

import re

MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"


def normalize_cv_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    for _ in range(3):
        text = re.sub(
            rf"([a-zA-Z])({MONTH})\s+(\d{{4}})",
            r"\1\n\2 \3",
            text,
            flags=re.IGNORECASE,
        )

    lines: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue

        if (
            lines
            and lines[-1]
            and re.match(r"^[a-z]", line)
            and not re.match(rf"^{MONTH}\s+\d{{4}}", line, re.IGNORECASE)
            and not re.match(r"^(?:present|now|current)\b", line, re.IGNORECASE)
        ):
            lines[-1] = lines[-1] + line
        else:
            lines.append(line)

    return "\n".join(lines)
