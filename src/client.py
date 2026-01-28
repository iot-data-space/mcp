from openai import OpenAI
import csv
import json
import os
import sys
import time
client = OpenAI()

MCP_SERVER_URL = "INSERT THE URL OF THE MCP SERVER"

server_instructions = """
You are interacting with a data space that stores objects of multiple types.
Each object has attributes relevant to its type, including a special attribute
'located_in' that indicates its location. Users may ask about attributes for
specific objects, types, or locations. If the user asks about a specific object,
call read with object_id. If the user asks about a specific type, call read with
type_id. If the user asks about a location, use get_types to discover which types
contain the requested attribute or type description, then read by type_id and filter
with located_in.
"""

prompts_path = os.path.join(os.path.dirname(__file__), "prompts.json")
with open(prompts_path, "r", encoding="utf-8") as file:
    prompts = json.load(file)

def _get_field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


writer = csv.writer(sys.stdout)
writer.writerow([
    "input",
    "output",
    "expected",
    "matches_expected",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "mcp_calls",
    "execution_time",
    "response_time_seconds"
])

for prompt in prompts:
    user_input = prompt["question"]
    expected_output = str(prompt["response"]).strip()
    start_time = time.perf_counter()
    response = client.responses.create(
        model="gpt-5.2",
        input=user_input,
        tools=[
            {
                "type": "mcp",
                "server_label": "mcp",
                "server_description": server_instructions,
                "server_url": MCP_SERVER_URL,
                "require_approval": "never",
            }
        ],
    )
    
    elapsed = time.perf_counter() - start_time
    output_text = (response.output_text or "").strip()
    mcp_calls = [
        item for item in (response.output or [])
        if _get_field(item, "type") == "mcp_call"
    ]
    usage = response.usage or {}
    created_at = _get_field(response, "created_at")
    completed_at = _get_field(response, "completed_at")
    execution_time = None
    if created_at is not None and completed_at is not None:
        try:
            # created_at/completed_at are unix timestamps; normalize to seconds.
            execution_time = (completed_at - created_at) / 1000.0 if completed_at > 1e12 else (completed_at - created_at)
        except TypeError:
            execution_time = None
    writer.writerow([
        user_input,
        output_text,
        expected_output,
        output_text == expected_output,
        _get_field(usage, "input_tokens"),
        _get_field(usage, "output_tokens"),
        _get_field(usage, "total_tokens"),
        len(mcp_calls),
        execution_time,
        f"{elapsed:.3f}"
    ])
    #print(response.model_dump_json())
