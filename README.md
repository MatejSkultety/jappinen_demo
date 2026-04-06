# AI Data Analyst PoC

Very small Streamlit proof of concept for uploading Excel files and asking simple data-quality questions.

## What it does

- Upload `.xlsx` files to a local folder.
- Load one uploaded file into a local SQLite database.
- Use Chat to ask simple questions about tables, rows, columns, missing values, and basic profiling.

## Run locally

1. Create a virtual environment.
2. Install dependencies:

	```bash
	pip install -r requirements.txt
	```

3. Set environment variables:

	- `OPENAI_API_KEY`

4. Start the app:

	```bash
	streamlit run app.py
	```

## Run with Docker Compose

1. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY`.
2. Start the app:

	```bash
	docker compose up --build
	```

## Environment variables

- `OPENAI_API_KEY` - required for chat routing.
