import fitz
import requests
import json
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stored_pdf_text = ""
stored_filename = ""


class QuestionRequest(BaseModel):
    question: str


def ask_ollama(prompt: str):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "No answer generated.")
    except Exception as e:
        return f"AI error: {str(e)}"


def extract_pdf_text(file_bytes: bytes):
    text = ""
    pdf = fitz.open(stream=file_bytes, filetype="pdf")

    for page in pdf:
        text += page.get_text() + "\n"

    return text.strip()


def is_general_question(question: str):
    q = question.lower().strip()

    general_phrases = [
        "explain",
        "explain this",
        "summarize",
        "summary",
        "teach me",
        "make it simple",
        "simplify",
        "what is this about",
        "help me understand",
        "break it down",
        "overview",
        "main idea",
        "key points",
        "important points",
        "study guide",
        "notes",
        "review",
    ]

    return q in general_phrases or len(q.split()) <= 3


def clean_markdown(text: str):
    text = text.replace("**", "")
    text = text.replace("* ", "• ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@app.get("/")
def home():
    return {"message": "Ultra IQ backend is running"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global stored_pdf_text, stored_filename

    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Please upload a PDF file."}

    file_bytes = await file.read()
    extracted_text = extract_pdf_text(file_bytes)

    if not extracted_text:
        return {"error": "Could not extract text from this PDF."}

    stored_pdf_text = extracted_text
    stored_filename = file.filename

    return {
        "message": f"{file.filename} uploaded successfully.",
        "filename": file.filename,
        "characters_extracted": len(extracted_text),
        "preview": extracted_text[:700],
    }


@app.post("/ask")
def ask_question(request: QuestionRequest):
    global stored_pdf_text, stored_filename

    question = request.question.strip()

    if not question:
        return {"answer": "Please type a question first."}

    if not stored_pdf_text:
        prompt = f"""
You are Ultra IQ, a helpful AI study assistant.

The user has not uploaded a PDF yet, so answer using your general knowledge.

User question:
{question}

Format your answer professionally using:
- Clear headings
- Short paragraphs
- Bullet points only when helpful
- No Markdown symbols like ** or *
"""
        answer = ask_ollama(prompt)
        return {"answer": clean_markdown(answer)}

    pdf_context = stored_pdf_text[:14000]

    if is_general_question(question):
        prompt = f"""
You are Ultra IQ, a professional AI study assistant.

The user uploaded a PDF named: {stored_filename}

The user asked:
"{question}"

Your job:
Explain the uploaded PDF clearly and professionally.

STRICT FORMAT RULES:
Do not use Markdown symbols.
Do not use **.
Do not use raw asterisks.
Do not write giant paragraphs.
Use clean headings.
Use short paragraphs.
Use bullet points with this symbol only: •

Answer in this exact structure:

Overview
Write 2-3 sentences explaining what the PDF is about.

Main Ideas
• First main idea
• Second main idea
• Third main idea

Simple Explanation
Explain the topic in beginner-friendly language.

Important Terms
• Term: simple meaning
• Term: simple meaning
• Term: simple meaning

What You Should Focus On
• Key thing to study
• Key thing to practice
• Key thing to remember

Suggested Questions To Ask Next
• Question 1
• Question 2
• Question 3

PDF content:
{pdf_context}
"""
    else:
        prompt = f"""
You are Ultra IQ, a professional AI study assistant.

The user uploaded a PDF named: {stored_filename}

Question:
{question}

Use the PDF as the main source. If the PDF does not directly answer the question, say what the PDF does say, then add a helpful explanation.

STRICT FORMAT RULES:
Do not use Markdown symbols.
Do not use **.
Do not use raw asterisks.
Do not write giant paragraphs.
Use clean headings.
Use short paragraphs.
Use bullet points with this symbol only: •

Answer in this structure:

Direct Answer
Answer the user's question clearly.

Explanation From The PDF
Explain the relevant PDF content.

Important Details
• Detail 1
• Detail 2
• Detail 3

Simple Takeaway
Give the user a simple final takeaway.

PDF content:
{pdf_context}
"""

    answer = ask_ollama(prompt)
    return {"answer": clean_markdown(answer)}


@app.post("/quiz")
def generate_quiz():
    global stored_pdf_text

    if not stored_pdf_text:
        return {"quiz": [], "message": "Upload a PDF first."}

    prompt = f"""
You are Ultra IQ.

Create exactly 5 multiple-choice quiz questions from the PDF.

Return ONLY valid JSON.
Do not include explanations.
Do not include Markdown.

Format:
[
  {{
    "question": "Question text here",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "Correct option text here"
  }}
]

PDF:
{stored_pdf_text[:12000]}
"""

    raw = ask_ollama(prompt)

    try:
        quiz = json.loads(raw)
        return {"quiz": quiz}
    except:
        return {
            "quiz": [
                {
                    "question": "Could not format quiz automatically. Try again.",
                    "options": ["Try again", "Upload PDF again", "Restart backend", "Check Ollama"],
                    "answer": "Try again",
                }
            ]
        }


@app.post("/flashcards")
def generate_flashcards():
    global stored_pdf_text

    if not stored_pdf_text:
        return {"flashcards": [], "message": "Upload a PDF first."}

    prompt = f"""
You are Ultra IQ.

Create exactly 8 study flashcards from the PDF.

Return ONLY valid JSON.
Do not include explanations.
Do not include Markdown.

Format:
[
  {{
    "front": "Question or term",
    "back": "Answer or explanation"
  }}
]

PDF:
{stored_pdf_text[:12000]}
"""

    raw = ask_ollama(prompt)

    try:
        flashcards = json.loads(raw)
        return {"flashcards": flashcards}
    except:
        return {
            "flashcards": [
                {
                    "front": "Could not format flashcards automatically.",
                    "back": "Try clicking Generate Flashcards again. Local models sometimes return invalid JSON.",
                }
            ]
        }