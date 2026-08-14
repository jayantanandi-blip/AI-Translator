# Jay's AI Translation Studio

AI Translation Studio is a Generative AI-powered web application built using Streamlit, Google Gemini API, and Google Text-to-Speech (gTTS). It enables users to translate text into multiple languages, convert the translated text into speech, and download the generated audio file.

# AI Translator

This Streamlit app translates text (or text extracted from uploaded files) into a chosen language, generates speech from the translated text using gTTS, and lets users download the resulting MP3.

# Quick Start/Setup:
1. Invoke a Python Virtual Environment:

```bash
python -m venv venv
```

2. Activate the Virtual Environment:

```bash
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. (Optional) Export your Gemini API configuration when you have credentials. The app looks for `GEMINI_API_KEY` and optional `GEMINI_ENDPOINT`/`GEMINI_MODEL`. If `GEMINI_API_KEY` is not set, the app will skip remote translation and use the original text so you can test TTS locally.

5. Run the app:

```bash
streamlit run app.py
```

6. Now program will launch the application with below URL:
http://localhost:8501/

## Features
- Translate plain text into multiple languages
- Powered by Google Gemini API for efficient translation
- Upload and translate TXT, CSV, Excel, and PDF files
- Configure the Gemini API key from the sidebar
- Convert translated text to speech using Google Text-To-Speech converted (gTTS)
- Generate MP3 audio from the translated text
- Download translated speech as an MP3 file


## Notes
- The Gemini API key is required for translation.
- The app uses the Google Gemini API endpoint with an API key.

## How to Use
1. Launch the application with http://localhost:8501/
2. Enter the API Key as generated with Gemini API Key
3. Enter the text or Upload the file you want to translate
4. Select the target language
5. Click "Translate + Generate Audio" button to Generate the Translation of the Text entered into Input window
6. Review the translated text
7. Listen to the generated audio
8. Download the MP3 file


## Supported Languages
The current user interface supports:
- Arabic
- Bengali
- Chinese
- English
- French
- German
- Hindi
- Japanese
- Korean
- Portuguese
- Russian
- Spanish