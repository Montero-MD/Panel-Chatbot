import panel as pn
from panel.chat import ChatInterface
import google.generativeai as genai
import tiktoken
from dotenv import load_dotenv
import os
import io
import pandas as pd
import docx
import fitz  # PyMuPDF

pn.extension()

# Load API key from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("No Gemini API key found in .env file")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Tokenizer
def count_tokens(text: str) -> int:
    encoding = tiktoken.encoding_for_model("gpt-4o-mini")
    tokens = encoding.encode(text)
    return len(tokens)

def extract_file_content(file):
    filename = file.filename
    file_extension = filename.split(".")[-1].lower()

    if file_extension in ["doc", "docx"]:
        try:
            doc = docx.Document(io.BytesIO(file.value))
            file_content = "\\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            return f"Error extracting DOCX: {e}"
    elif file_extension == "pdf":
        try:
            pdf_document = fitz.open(stream=io.BytesIO(file.value), filetype="pdf")
            file_content = ""
            for page in pdf_document:
                file_content += page.get_text()
            pdf_document.close()
        except Exception as e:
            return f"Error extracting PDF: {e}"
    elif file_extension in ["csv", "xls", "xlsx"]:
        try:
            df = pd.read_excel(io.BytesIO(file.value))
        except Exception as e:
            try:
                df = pd.read_csv(io.BytesIO(file.value))
            except Exception as e:
                return f"Error extracting CSV/Excel: {e}"
        file_content = df.to_csv()
    elif file_extension == "txt":
        file_content = file.value.decode("utf-8")
    else:
        return "Unsupported file format"

    return file_content

# Callback function
def callback(contents: str, user: str, instance: ChatInterface):
    # Add instructions to Gemini
    instructions =  """
As a data analysis expert, your role is to interpret complex numerical data, offer recommendations, and evaluate activities using statistical methods to gain insights across different areas of environmental, social and governance sustainability.
Accuracy is the top priority. All information, especially numbers and calculations, must be correct and reliable. Always double-check for errors before giving a response. The way you respond should change based on what the user needs. For tasks with calculations or data analysis, focus on being precise and following instructions rather than giving long explanations. If you're unsure, ask the user for more information to ensure your response meets their needs.

For tasks that are not about numbers:

* Use clear and simple language, avoiding jargon and confusion.
* Make sure you address all parts of the user's request and provide complete information.
* Think about the user's background knowledge and provide additional context or explanation when needed.

Formatting and Language:

* Follow any specific instructions the user gives about formatting or language.
* Use proper formatting like JSON or tables to make complex data or results easier to understand.
""".strip()
    # Get file contents if available
    file_contents = ""
    if file_input.value:
        file_contents = extract_file_content(file_input)

    prompt = instructions + "\\n" + contents + "\\n" + file_contents

    # Tokenize and truncate if necessary
    token_count = count_tokens(prompt)
    if token_count > 2048:
        prompt = prompt[:2048]  # Truncate to the first 2048 tokens
        return "Error: Prompt exceeds token limit. Prompt was truncated."

    # Send prompt to Gemini API
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# Chat interface
file_input = pn.widgets.FileInput(accept='.doc,.docx,.csv,.xls,.xlsx,.pdf,.txt')
chat_interface = ChatInterface(callback=callback, objects=[file_input])

pn.serve(chat_interface, show=True)
