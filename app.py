"""AI Translator Streamlit app

Features:
- Paste text or upload PDF/TXT/CSV/XLSX
- Translate using a Gemini API (placeholder HTTP call)
- Convert translated text to speech using gTTS and provide MP3 download

Notes:
- The Gemini translation call is a placeholder; replace with the official SDK or endpoint and adapt response parsing.
"""

from __future__ import annotations

import os
import tempfile
import typing
import streamlit as st
from gtts import gTTS
import pandas as pd
import PyPDF2
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; requirements include python-dotenv for convenience
    pass

st.set_page_config(page_title="AI Translator", layout="centered")

# Sidebar: allow user to provide Gemini API settings interactively
st.sidebar.header("Gemini API (optional)")
# Only ask for API key in the UI; model is chosen by default in code.
gemini_api_key_input = st.sidebar.text_input("Gemini API Key", value=os.environ.get("GEMINI_API_KEY", ""), type="password")

# Try to import official Google Gemini / Generative SDKs if available.
SDK_AVAILABLE = False
try:
    import google.generativeai as genai  # type: ignore
    SDK_AVAILABLE = True
except Exception:
    genai = None

try:
    from google import genai as google_genai  # type: ignore
    SDK_AVAILABLE = True
except Exception:
    google_genai = None

# Default model requested by the user. Override with GEMINI_MODEL if needed.
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

# Map display names to ISO codes used by gTTS and (typically) translation APIs.
LANGUAGE_CODES = {
    "Arabic": "ar",
    "Bengali": "bn",
    "Chinese (Simplified)": "zh",
    "English": "en",
    "French": "fr",
    "German": "de",
    "Hindi": "hi",
    "Japanese": "ja",
    "Korean": "ko",
    "Portuguese": "pt",
    "Russian": "ru",
    "Spanish": "es",
}

# Reverse map for code -> display name (used to build human-friendly prompts)
CODE_TO_NAME = {v: k for k, v in LANGUAGE_CODES.items()}


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """Extract text from uploaded file-like object.

    Supports: pdf, txt, csv, xls, xlsx
    Returns a string with extracted text (may be large).
    """
    name = uploaded_file.name.lower()
    ext = name.split(".")[-1]
    try:
        if ext == "pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            pages = [p.extract_text() or "" for p in reader.pages]
            return "\n".join(pages)
        elif ext in ("xls", "xlsx"):
            df = pd.read_excel(uploaded_file)
            return df.astype(str).apply(lambda row: " ".join(row.values), axis=1).str.cat(sep="\n")
        elif ext == "csv":
            df = pd.read_csv(uploaded_file)
            return df.astype(str).apply(lambda row: " ".join(row.values), axis=1).str.cat(sep="\n")
        else:  # txt or unknown: try decode
            return uploaded_file.getvalue().decode("utf-8")
   
    except Exception:
        # Let caller handle reporting errors to the user
        raise ValueError("Unsupported file type. Please upload either a .txt, .pdf, or .csv file only!!")

def chunk_text(text: str, max_chars: int = 4000) -> list[str]:
    """Split long text into chunks not exceeding `max_chars` characters.

    This helps with TTS and API limits. Splits on sentence boundaries when possible.
    """
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Try to backtrack to a newline or sentence end for nicer splits
        if end < len(text):
            bk = text.rfind("\n", start, end)
            if bk == -1:
                bk = text.rfind(". ", start, end)
            if bk != -1 and bk > start:
                end = bk + 1
        chunks.append(text[start:end].strip())
        start = end
    return chunks


def _extract_text_from_gemini_response(response) -> str:
    """Normalize Gemini API responses into a plain translated string."""
    if response is None:
        return ""
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        for key in ("text", "translated_text", "content", "output_text"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if "candidates" in response and isinstance(response["candidates"], list):
            first = response["candidates"][0]
            if isinstance(first, dict):
                for key in ("content", "text"):
                    value = first.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                parts = first.get("parts") or []
                texts: list[str] = []
                for part in parts:
                    if isinstance(part, dict):
                        text = part.get("text")
                        if isinstance(text, str):
                            texts.append(text)
                    elif isinstance(part, str):
                        texts.append(part)
                if texts:
                    return "".join(texts).strip()
        return str(response).strip()

    for attr in ("text", "content"):
        if hasattr(response, attr):
            value = getattr(response, attr)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                texts = []
                for item in value:
                    if isinstance(item, str):
                        texts.append(item)
                    elif isinstance(item, dict) and isinstance(item.get("text"), str):
                        texts.append(item["text"])
                if texts:
                    return "".join(texts).strip()

    if hasattr(response, "candidates"):
        candidate_list = getattr(response, "candidates")
        if isinstance(candidate_list, list) and candidate_list:
            first = candidate_list[0]
            text = getattr(first, "text", None)
            if isinstance(text, str) and text.strip():
                return text.strip()
            if hasattr(first, "content"):
                content = getattr(first, "content")
                return _extract_text_from_gemini_response(content)

    return str(response).strip()


def translate_text_gemini(text: str, target_lang: str, api_key: str | None = None, model: str | None = None) -> str:
    """Translate `text` to `target_lang` using the official Gemini API SDK when available."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    model = model or DEFAULT_MODEL
    if not api_key:
        return text

    lang_name = CODE_TO_NAME.get(target_lang, target_lang)
    prompt = f"Translate the following text to {lang_name}. Return only the translated text with no extra commentary:\n\n{text}"

    try:
        if google_genai is not None:
            client = google_genai.Client(api_key=api_key)
            response = client.models.generate_content(model=model, contents=prompt)
            extracted = _extract_text_from_gemini_response(response)
            if extracted:
                return extracted

        if genai is not None:
            try:
                genai.configure(api_key=api_key)
            except Exception:
                pass
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            extracted = _extract_text_from_gemini_response(response)
            if extracted:
                return extracted
    except Exception:
        pass

    # Fallback for environments where only a generic HTTP proxy is configured.
    url = os.environ.get("GEMINI_ENDPOINT") or "https://api.example.com/v1/translate"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": text, "target_language": target_lang}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            for key in ("translated_text", "text", "output_text"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return text
    except Exception:
        raise


st.title("Welcome to Jay's AI Translator: Translate Word & Sentences, Convert to Speech and Download the Speech!")

st.markdown("1. Set Gemini API Key in the sidebar, the app will return the Translated text & Generate Speech with Click of a Button.")
st.markdown("2. Enter Text or Upload a file (PDF, TXT, CSV, XLSX)")
st.markdown("3. Choose a target language, then translate and download audio.")

# Input selection
input_mode = st.radio("Input mode", ("Text", "File upload"))

user_text = ""
if input_mode == "Text":
    user_text = st.text_area("Enter text to translate", height=200)
else:
    uploaded_file = st.file_uploader("Upload a file", type=["pdf", "txt", "csv", "xls", "xlsx"])
    if uploaded_file is not None:
        try:
            user_text = extract_text_from_uploaded_file(uploaded_file)
        except Exception as e:
            st.error(f"Failed to read uploaded file: {e}")


target_language = st.selectbox("Target language", list(LANGUAGE_CODES.keys()), index=0)


if st.button("Translate + Generate Audio"):
    if not user_text or user_text.strip() == "":
        st.warning("Please provide text or upload a valid file to translate.")
    else:
        translated = ""
        # Attempt translation and show a helpful error if it fails
        try:
            with st.spinner("Translating..."):
                translated = translate_text_gemini(
                    user_text,
                    LANGUAGE_CODES[target_language],
                    api_key=gemini_api_key_input or None,
                )
        except Exception as e:
            st.error(f"Translation failed: {e}\nUsing original text for TTS.")
            translated = user_text

        st.subheader("Translated Text")
        st.text_area("", translated, height=200)

        # Use chunking to avoid long-text issues with gTTS
        chunks = chunk_text(translated, max_chars=3000)
        tts_lang = LANGUAGE_CODES[target_language]
        audio_bytes = bytearray()
        tmp_names: list[str] = []
        try:
            with st.spinner("Generating speech (gTTS)..."):
                for i, chunk in enumerate(chunks):
                    tts = gTTS(text=chunk, lang=tts_lang)
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{i}.mp3")
                    tmp_name = tmp.name
                    tmp.close()
                    tts.save(tmp_name)
                    tmp_names.append(tmp_name)
                    with open(tmp_name, "rb") as f:
                        audio_bytes.extend(f.read())

            # Present audio and download; we join MP3 byte streams which works
            # well for simple cases. For production, consider merging with pydub.
            st.audio(bytes(audio_bytes))
            st.download_button(label="Download audio (MP3)", data=bytes(audio_bytes), file_name="translation.mp3", mime="audio/mpeg")
        except Exception as e:
            st.error(f"Failed to generate or serve audio: {e}")
        finally:
            # Cleanup temporary files
            for fn in tmp_names:
                try:
                    os.unlink(fn)
                except Exception:
                    pass

st.markdown("---")
st.markdown("Hints: Set GEMINI_API_KEY for real translations. If not set, the app returns the original text so you can test TTS locally.")
