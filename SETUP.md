# Setup

## 1. Create `.env`

Create a file named `.env` in the repository root and add your OpenAI API key:

```env
OPENAI_API_KEY=your_key_here
```

## 2. Run locally

Create a virtual environment, install dependencies, and start Streamlit:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 3. Run with Docker

If you do not want to set up Python manually, run:

```bash
docker-compose up --build
```

## 4. Open the app

After startup, open:

http://localhost:8501

## 5. Use the app

Upload an Excel file in the file ingestion page, select the tables you want as context, and start chatting.
