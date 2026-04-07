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


def debug_log(label: str, value: object) -> None:
    print(f"[llm] {label}: {value}")


def build_context(selected_tables: list[str]) -> str:
    if not selected_tables:
        return "No tables are available."
    return "Available tables: " + ", ".join(selected_tables)


def execute_tool_call(tool_name: str, arguments_json: str, connection: sqlite3.Connection) -> object:
    debug_log(f"tool call -> {tool_name}", arguments_json)
    tool_registry = get_tool_registry()
    tool = tool_registry.get(tool_name)
    if tool is None:
        result = {"error": f"Tool not available: {tool_name}"}
        debug_log(f"tool return <- {tool_name}", result)
        return result

    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        result = {"error": f"Invalid arguments for tool: {tool_name}"}
        debug_log(f"tool return <- {tool_name}", result)
        return result

    try:
        result = tool["executor"](connection, arguments)
        debug_log(f"tool return <- {tool_name}", result)
        return result
    except Exception as exc:
        result = {"error": f"Tool failed: {tool_name}", "details": str(exc)}
        debug_log(f"tool return <- {tool_name}", result)
        return result


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
                "You can answer questions only in selected tables, not all tables in the database. "
                "You are an AI data analyst for simple SQLite-backed datasets. "
                "Use tools when you need table names, schema details, row counts, column lists, missing values, distinct counts, numeric stats, a table profile, or a read-only SQL query. "
                "If you use SQL, it must be a single read-only SELECT or WITH query only. Never ask for INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, ATTACH, or DETACH. "
                "Keep answers short, direct, and grounded in the tool results."
            ),
        },
        {"role": "system", "content": build_context(selected_tables)},
        *recent_messages,
        {"role": "user", "content": question},
    ]

    debug_log("selected tables", selected_tables)
    debug_log("conversation messages", recent_messages)
    debug_log("llm request messages", messages)

    for _ in range(TOOL_USAGE_LIMIT):
        debug_log("requesting completion", {"model": "gpt-4o-mini", "tool_count": len(get_tool_schemas())})
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=messages,
            tools=get_tool_schemas(),
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        debug_log("assistant message", assistant_message.model_dump(exclude_none=True))

        if not assistant_message.tool_calls:
            debug_log("final answer", assistant_message.content or "No answer was returned.")
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
                debug_log("llm tool message", {"tool": tool_call.function.name, "result": tool_result})

    return "The assistant could not finish the answer in time."
