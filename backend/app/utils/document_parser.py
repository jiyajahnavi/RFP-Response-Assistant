import io
import re
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
from docx import Document
import openpyxl
from app.utils.classifier import classify_question


def extract_questions_from_text(raw_text: str) -> List[Dict[str, Any]]:
    """
    Extracts distinct questions from raw multiline text.
    Handles numbered patterns (e.g. '1.', 'Q1:', '1.1', '[1]', etc.) or question mark endings.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    extracted = []
    current_question = []

    # Regex for numbered question start: e.g. "1.", "1)", "1.1", "Q1:", "Q1.", "Question 1:"
    question_start_pattern = re.compile(
        r"^((q(uestion)?\s*\d+[\.:\)]?)|(\d+(\.\d+)*[\.\)\:]))\s+",
        re.IGNORECASE
    )

    for line in lines:
        if question_start_pattern.match(line):
            if current_question:
                q_text = " ".join(current_question).strip()
                if len(q_text) > 5:
                    extracted.append(q_text)
                current_question = []
            # Strip initial numbering identifier
            cleaned = question_start_pattern.sub("", line).strip()
            current_question.append(cleaned)
        elif line.endswith("?") and not current_question:
            extracted.append(line)
        else:
            if current_question:
                current_question.append(line)
            elif line.endswith("?"):
                extracted.append(line)

    if current_question:
        q_text = " ".join(current_question).strip()
        if len(q_text) > 5:
            extracted.append(q_text)

    # Fallback: If no structured numbered items were detected, treat sentences ending with '?' as questions
    if not extracted:
        sentences = re.split(r"(?<=\?)\s+", raw_text)
        for s in sentences:
            s_clean = s.strip()
            if s_clean.endswith("?") and len(s_clean) > 8:
                extracted.append(s_clean)

    return [{"QuestionText": q, "Category": classify_question(q)} for q in extracted]


def parse_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
    reader = PdfReader(io.BytesIO(file_bytes))
    all_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            all_text.append(text)
    full_text = "\n".join(all_text)
    return extract_questions_from_text(full_text)


def parse_docx(file_bytes: bytes) -> List[Dict[str, Any]]:
    doc = Document(io.BytesIO(file_bytes))
    extracted = []

    # 1. Check tables first (very common in RFP questionnaires)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            for cell in cells:
                if len(cell) > 10 and (cell.endswith("?") or re.match(r"^(\d+|Q\d+)[\.\)]", cell, re.I)):
                    extracted.append(cell)

    # 2. Extract from paragraphs
    para_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    para_questions = extract_questions_from_text(para_text)

    combined_questions = []
    seen = set()

    # Add table questions first if any
    for q in extracted:
        clean_q = re.sub(r"^((q(uestion)?\s*\d+[\.:\)]?)|(\d+(\.\d+)*[\.\)\:]))\s+", "", q, flags=re.I).strip()
        if clean_q not in seen:
            seen.add(clean_q)
            combined_questions.append({
                "QuestionText": clean_q,
                "Category": classify_question(clean_q)
            })

    for item in para_questions:
        if item["QuestionText"] not in seen:
            seen.add(item["QuestionText"])
            combined_questions.append(item)

    return combined_questions


def parse_xlsx(file_bytes: bytes) -> List[Dict[str, Any]]:
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    questions = []
    seen = set()

    for sheetname in wb.sheetnames:
        sheet = wb[sheetname]
        # Identify headers if present
        header_indices = {}
        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            if row_idx == 1:
                for col_idx, cell_value in enumerate(row):
                    if cell_value and isinstance(cell_value, str):
                        val_lower = cell_value.strip().lower()
                        if "question" in val_lower or "requirement" in val_lower or "prompt" in val_lower:
                            header_indices["question"] = col_idx
                        elif "category" in val_lower or "section" in val_lower:
                            header_indices["category"] = col_idx
                continue

            q_text = None
            category = None

            if "question" in header_indices:
                val = row[header_indices["question"]]
                if val and isinstance(val, str) and len(val.strip()) > 5:
                    q_text = val.strip()
                if "category" in header_indices and header_indices["category"] < len(row):
                    cat_val = row[header_indices["category"]]
                    if cat_val and isinstance(cat_val, str):
                        category = cat_val.strip()
            else:
                # Scan cells in the row for question text
                for cell in row:
                    if cell and isinstance(cell, str) and (cell.strip().endswith("?") or len(cell.strip()) > 15):
                        q_text = cell.strip()
                        break

            if q_text and q_text not in seen:
                seen.add(q_text)
                if not category:
                    category = classify_question(q_text)
                questions.append({
                    "QuestionText": q_text,
                    "Category": category
                })

    return questions


def parse_document(filename: str, file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parses PDF, DOCX, or XLSX questionnaire files and returns structured questions with categories.
    """
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return parse_pdf(file_bytes)
    elif lower_name.endswith(".docx"):
        return parse_docx(file_bytes)
    elif lower_name.endswith(".xlsx"):
        return parse_xlsx(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {filename}. Supported formats: .pdf, .docx, .xlsx")
