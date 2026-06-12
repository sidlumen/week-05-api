#1.This is Claude telling your code: "I can't finish yet — I need to call a tool before I can answer." Instead of returning a final text answer
#2.This matters because Claude can request multiple tool calls in one turn.The tool_use_id is how Claude matches each result to the specific call that produced it — like a request/response correlation ID. Without it, Claude wouldn't know which result answers which question
#The Anthropic API only has two roles in the conversation: assistant (Claude's turns) and user (everything sent to Claude).
#This guarantees the function returns within a bounded number of API calls, even in the worst case — turning "infinite loop / hung request" into "agent gives up gracefully after N tries."
tools = [
    {
        "name": "get_books",
        "description": "Get books from the user's reading list, including each book's id, title, author, status, and rating. Use this first to look up a book's id before calling get_book_by_id, update_book, or delete_book. Can filter by status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by status: 'reading', 'read', or 'want_to_read'. Omit for all books.",
                    "enum": ["reading", "read", "want_to_read"]
                }
            },
            "required": []
        }
    },
    {
        "name": "add_book",
        "description": "Add a new book to the user's reading list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The book's title"
                },
                "author": {
                    "type": "string",
                    "description": "The book's author"
                },
                "status": {
                    "type": "string",
                    "description": "Reading status. Defaults to 'want_to_read' if omitted.",
                    "enum": ["reading", "read", "want_to_read"]
                },
                "rating": {
                    "type": "integer",
                    "description": "Rating from 1-5, only if the book has already been read."
                }
            },
            "required": ["title", "author"]
        }
    },
    {
        "name": "get_book_by_id",
        "description": "Get details about a specific book by its id. Use get_books first if you don't already know the book's id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book_id": {
                    "type": "integer",
                    "description": "The unique identifier for the book, as returned by get_books"
                }
            },
            "required": ["book_id"]
        }
    },
    {
        "name": "update_book",
        "description": "Update the reading status and/or rating of a specific book. Use get_books first if you don't already know the book's id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book_id": {
                    "type": "integer",
                    "description": "The unique identifier for the book, as returned by get_books"
                },
                "status": {
                    "type": "string",
                    "description": "The new reading status",
                    "enum": ["reading", "read", "want_to_read"]
                },
                "rating": {
                    "type": "integer",
                    "description": "Rating from 1-5, typically set once the book's status is 'read'"
                }
            },
            "required": ["book_id"]
        }
    },
    {
        "name": "delete_book",
        "description": "Permanently remove a book from the user's reading list. This cannot be undone, so only call it when the user clearly asks to delete or remove a book. Use get_books first if you don't already know the book's id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book_id": {
                    "type": "integer",
                    "description": "The unique identifier for the book, as returned by get_books"
                }
            },
            "required": ["book_id"]
        }
    }
]
import requests

API_URL = "http://localhost:8000"


def get_books_fn(status: str = None) -> list:
    url = f"{API_URL}/books"
    if status:
        url += f"?status={status}"
    return requests.get(url).json()


def add_book_fn(title: str, author: str, status: str = "want_to_read", rating: int = None) -> dict:
    payload = {"title": title, "author": author, "status": status, "rating": rating}
    return requests.post(f"{API_URL}/books", json=payload).json()


def get_book_by_id_fn(book_id: int) -> dict:
    return requests.get(f"{API_URL}/books/{book_id}").json()


def update_book_fn(book_id: int, status: str = None, rating: int = None) -> dict:
    payload = {"status": status, "rating": rating}
    return requests.put(f"{API_URL}/books/{book_id}", json=payload).json()


def delete_book_fn(book_id: int) -> dict:
    return requests.delete(f"{API_URL}/books/{book_id}").json()


tool_functions = {
    "get_books": get_books_fn,
    "add_book": add_book_fn,
    "get_book_by_id": get_book_by_id_fn,
    "update_book": update_book_fn,
    "delete_book": delete_book_fn,
}

import anthropic
import json

client = anthropic.Anthropic()

MAX_ITERATIONS = 10


def run_agent(user_message: str, tools: list, tool_functions: dict) -> tuple[str, list]:
    """
    Runs the agent loop until Claude returns a final text response.
    tool_functions: dict mapping tool name → callable Python function
    Returns (reply_text, agent_steps) where agent_steps logs each tool call made.
    """
    messages = [{"role": "user", "content": user_message}]
    agent_steps = []

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        # Add Claude's response to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Claude is done — extract the text response
            text_blocks = [block.text for block in response.content if hasattr(block, "text")]
            reply = "\n".join(text_blocks) if text_blocks else "No response generated"
            return reply, agent_steps

        elif response.stop_reason == "tool_use":
            # Claude wants to use a tool
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"[Agent] Calling tool: {tool_name} with {tool_input}")

                    # Execute the actual function
                    if tool_name in tool_functions:
                        result = tool_functions[tool_name](**tool_input)
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    agent_steps.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            # Give the tool results back to Claude
            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason (e.g. max_tokens) — return whatever text we have
            text_blocks = [block.text for block in response.content if hasattr(block, "text")]
            reply = "\n".join(text_blocks) if text_blocks else "Agent finished unexpectedly"
            return reply, agent_steps

    return "Agent gave up after too many steps", agent_steps
