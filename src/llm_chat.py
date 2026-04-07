from __future__ import annotations

import json
import os
import sqlite3

from openai import OpenAI
from dotenv import load_dotenv

from .db import get_connection
from .tool_registry import get_tool_registry, get_tool_schemas


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CONTEXT_SIZE = 20
TOOL_USAGE_LIMIT = 10


def build_context(selected_tables: list[str]) -> str:
    if not selected_tables:
        return "No tables are available."
    return "Available tables: " + ", ".join(selected_tables)


def execute_tool_call(tool_name: str, arguments_json: str, connection: sqlite3.Connection) -> object:
    tool_registry = get_tool_registry()
    tool = tool_registry.get(tool_name)
    if tool is None:
        return {"error": f"Tool not available: {tool_name}"}

    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return {"error": f"Invalid arguments for tool: {tool_name}"}

    try:
        return tool["executor"](connection, arguments)
    except Exception as exc:
        return {"error": f"Tool failed: {tool_name}", "details": str(exc)}


def ask_data_question(
    question: str,
    selected_tables: list[str],
    conversation_messages: list[dict[str, str]] | None = None,
) -> str:
    if not OPENAI_API_KEY:
        return "OpenAI API key is missing."

    client = OpenAI(api_key=OPENAI_API_KEY)
    recent_messages = (conversation_messages or [])[-CONTEXT_SIZE:]
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI data analyst for simple SQLite-backed datasets. "
                "Use tools when you need table names, row counts, column lists, missing values, or a table profile. "
                "Keep answers short, direct, and grounded in the tool results."
            ),
        },
        {"role": "system", "content": build_context(selected_tables)},
        *recent_messages,
        {"role": "user", "content": question},
    ]

    for _ in range(TOOL_USAGE_LIMIT):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=messages,
            tools=get_tool_schemas(),
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message

        if not assistant_message.tool_calls:
            return assistant_message.content or "No answer was returned."

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in assistant_message.tool_calls
                ],
            }
        )

        with get_connection() as connection:
            for tool_call in assistant_message.tool_calls:
                tool_result = execute_tool_call(tool_call.function.name, tool_call.function.arguments, connection)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result),
                    }
                )

    return "The assistant could not finish the answer in time."
