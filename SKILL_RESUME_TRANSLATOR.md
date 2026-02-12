---
name: Generic Resume AI Translator
description: Instructions for an AI Agent to translate ANY French resume to English while perfectly preserving look and feel.
---

# 🤖 Generic Resume AI Translator Skill

This skill allows an AI Agent to take any French DOCX resume and generate a pixel-perfect English version (DOCX + PDF).

## 🛠 Required Tools
- `run_translation_pipeline.py` (The surgical XML engine)
- Any LLM (for the actual translation of strings)

## 🔄 Universal Workflow for Any CV

### MODE A: Agent Is Capable of Running Scripts (Recommended)
Follow the standard 3-step pipeline (Extract -> Translate -> Generate) using `run_translation_pipeline.py`. This is the only way to guarantee 100% UI preservation with zero effort.

---

### MODE B: Agent Is Restricted (Cannot Run Scripts)
If you cannot execute the Python engine, you must guide the USER to perform a manual XML swap to preserve the UI:

1.  **Request the XML**: Ask the USER to rename `CV_FR.docx` to `CV_FR.zip`, extract `word/document.xml`, and upload the text of that XML to the chat.
2.  **Perform "Context-Aware" Translation**:
    - Search for `<w:t>` tags in the XML.
    - Translate the text *inside* these tags while leaving the XML tags (`<...>`) completely untouched.
    - **Crucial**: If a sentence is split across multiple `<w:t>` tags, translate the whole sentence into the first tag and leave the others empty (`<w:t></w:t>`).
3.  **Provide the Translated XML**: Give the modified XML back to the USER.
4.  **Final Assembly**: Instruct the USER to:
    - Replace the original `word/document.xml` inside the `.zip` with your translated version.
    - Rename the `.zip` back to `.docx`.
    - Open in Word and "Save as PDF".

---

## 📦 Deliverables
- `[OriginalName]_EN.docx`
- `[OriginalName]_EN.pdf`

---
*Strategy: Surgical XML editing (whether automated by script or manual by agent) is the only way to preserve 100% of formatting, fonts, and UI elements.*

