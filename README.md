# AI Data Analyst PoC

I built this proof of concept as a small Streamlit app for non-technical users who need quick answers about data quality and basic profiling.

## What I built

I've used Streamlit for a fast and simple UI prototype. The app has two pages only: one for file ingestion and one for chat. Excel sheets are loaded into SQLite, and the chat page lets the user pick tables for context before asking questions in plain language.

I've used SQLite because it is lightweight and keeps the setup simple (storing to file).

Data Management page was introduced to show how we can add or delete different datasheets (currently only Excel files). User can select only some of uploaded tables in the Chat interface. I believe this shows additional functionality which would more appreciated by non-technical users then fine tuned agentic workflow. 

For the AI part, I use the OpenAI API with `gpt-4o-mini`. I kept a small set of tools for table inspection and profiling, which are used by the LLM. After testing I've also decided to add read-only SQL tool for more flexible questions. The code checks that SQL stays read only and all destructive queries are disabled to LLM. I didn't create complex agentic workflow, since current setup provides good enough answers for simple questions which could be asked on a intro demo with non-technical users (or at least to questions that came up my mind). 

I've also added simple docker-compose file for simple setup. App can be run either in Docker or directly with Python (virtual environment is advised) - see SETUP.md.

## Architecture

The app is split into a few small parts:

- `app.py` sets up Streamlit navigation.
- `pages/1_Data_Management.py` handles Excel upload and dataset deletion.
- `pages/2_Chat.py` handles the chat UI and conversation state.
- `src/db.py` contains SQLite helpers.
- `src/profiling.py` contains simple data analysis helpers.
- `src/tool_registry.py` lists the tools the LLM is allowed to use.
- `src/llm_chat.py` contains the LLM flow, tool calling, and answer generation.

I avoided classes and heavy abstractions because this is a PoC, not a full product.

## How to run it

See [SETUP.md](SETUP.md) for the exact steps.

## How to use it

Upload an Excel file in Data Management page. In a Chat page select the tables you want as context, and ask a question. The app can answer simple data-quality and profiling questions such as row counts, missing values, distinct counts, basic numeric stats. For more specific questions, LLM will create read-only SQL queries. LLM carries context from entire conversation and can use up to 10 tool calls per question (it's a lot and it probbably won't hit the limit with current configuration, but it still seemed fast as it is).

## What I left out

I did not separate database service and I did not build FasAPI backend (overkill in my opinion).

I also did not build a full agent framework and I did not use LangChain, since OpenAI client was good enough for this PoC. 

The UI deserved more love, I am aware of some strange behavior with table selection buttons.

There is no real error handling and logging. I've only added logs into LLM flow so I know what's going on under the hood.

No unit tests were added. If I had more time, I would use pytest since entire project is written in Python.

Currently there is no conversations history. User is only able to reset current conversation.

## AI declaration

I used AI assistance while building this project for:

- Brainstorming the assignment structure.

- Code autocompletion (GitHub Copilot).

- Reviewing my changes.

- Identifying database tools for LLM use.

- Fine-tuning the system prompt.

I designed, tested, and implemented the entire app myself, using AI as a supportive learning tool. This aligns with how I personally use AI for daily development, and I believe it is well within the expectations for this assignment. Thanks!
