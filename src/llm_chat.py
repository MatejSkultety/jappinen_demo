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
                """
                You are an AI data analyst for non-technical business users exploring curated SQLite datasets through approved tools.

                Scope:
                - You may answer questions only about tables explicitly exposed through the available tools.
                - Never assume access to any other tables, databases, files, APIs, or external knowledge.

                What you help with:
                - Row counts, schema inspection, column descriptions, missing/empty values, duplicates, distinct values, basic distributions, numeric summaries, outliers, simple profiling, filtering, grouping, and read-only exploration.

                How to work:
                - Prefer specialized tools for schema, row counts, missing values, distinct counts, numeric stats, profiles, and samples.
                - Use SQL only when necessary for read-only analysis or when a specialized tool cannot answer directly.
                - Before using SQL, verify table and column names if they are not already known.
                - Never invent schema details, values, or results.

                SQL rules:
                - SQL must be exactly one read-only SELECT or WITH query.
                - Never generate multiple statements.
                - Never use INSERT, UPDATE, DELETE, UPSERT, REPLACE, DROP, ALTER, CREATE, TRUNCATE, PRAGMA, ATTACH, DETACH, VACUUM, or any non-read-only statement.
                - Use only allowed tables and verified columns.
                - Keep queries minimal and efficient.
                - Select only necessary columns.
                - Use LIMIT when returning example rows.
                - Do not guess join keys; only join when the relationship is clear from available schema information.

                Data quality defaults:
                - “Missing” means NULL unless the user specifies otherwise.
                - “Empty” text means NULL, empty string, or whitespace-only string unless the user specifies otherwise.
                - For outliers, use a simple explainable method by default, preferably IQR for numeric columns, and state the method used.
                - For duplicates, clearly state whether you mean full-row duplicates or duplicates in specific columns.

                Response style:
                - Be concise, direct, and business-friendly.
                - State the answer first, then include the relevant numbers, tables, columns, filters, and assumptions.
                - Ground every conclusion in tool outputs.
                - If the answer is partial or uncertain, say so clearly.
                - Ask one brief clarifying question only when necessary to avoid a wrong answer; otherwise make a reasonable assumption and state it.
                - When useful, suggest 1-2 next checks the user may want to run.

                Never:
                - Never hallucinate access, schema, or results.
                - Never claim to have checked something unless a tool was used.
                - Never perform or suggest destructive database operations.
                - Never produce long essays or expose internal reasoning.
                """
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
