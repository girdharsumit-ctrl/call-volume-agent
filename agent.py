"""Steps 4 and 5: the instructions and the agent loop.

Run:  python agent.py data/sample_calls_4wk.csv "Which hours get the most calls?"
The key is read from the ANTHROPIC_API_KEY environment variable.
"""
import json
import os
import sys

import anthropic

from tools import hourly_call_volume, make_hourly_chart

MODEL = "claude-sonnet-5-5"
MAX_STEPS = 6  # safety limit so the loop can never run forever

# ---- Step 4: the instructions. This is where the domain knowledge goes. Edit freely. ----
SYSTEM = """You help a contact center manager understand call volume.

The data has 15-minute intervals with three columns: interval_start, queue, and calls_offered
(calls that reached the queue).

Rules:
- Always get numbers from the tools. Never calculate or estimate numbers yourself.
- Write in plain language for a manager who may not know contact center terms.
- Name the busiest hours first, with the average calls in that hour on a typical day.
  Write hours as 10am, 2pm.
- If an hour has fewer days open than the others, say so briefly.
- Keep the answer under 120 words.
- After you name the busiest hours, also create the chart with the chart tool. The file location
  is added to your answer automatically, so do not write it yourself.
- You only have call counts, so do not guess at causes.
"""

# ---- Tool description: this is what Claude sees. It never sees the code itself. ----
TOOLS = [
    {
        "name": "get_hourly_volume",
        "description": (
            "Rolls the 15-minute call data up to hours. Returns one row per hour of the day with "
            "total_calls, days_open (days that hour was open) and avg_calls (average calls in that "
            "hour on a typical day). Optionally limit to one queue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "queue": {"type": "string", "description": "Queue name. Leave out for all queues combined."}
            },
        },
    },
    {
        "name": "make_hourly_chart",
        "description": (
            "Draws a bar chart of average calls per hour on a typical day and saves it as an image "
            "file. Returns the file path. Optionally limit to one queue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "queue": {"type": "string", "description": "Queue name. Leave out for all queues combined."}
            },
        },
    },
]


def run_tool(name, tool_input, csv_path):
    """Our code runs the tool. Claude only asks for it."""
    if name == "get_hourly_volume":
        table = hourly_call_volume(csv_path, tool_input.get("queue"))
        return json.dumps(table.to_dict(orient="records"))
    if name == "make_hourly_chart":
        return make_hourly_chart(csv_path, queue=tool_input.get("queue"))
    raise ValueError(f"Unknown tool: {name}")


# ---- Step 5: the agent loop ----
def run_agent(question, csv_path, client=None):
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": question}]
    chart_paths = []  # filled in by our code, so the file location never depends on Claude's wording

    for _ in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break  # Claude has written its final answer

        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[tool call] {block.name} {block.input}")
                try:
                    output = run_tool(block.name, block.input, csv_path)
                    if block.name == "make_hourly_chart":
                        chart_paths.append(os.path.abspath(output))
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
                except Exception as e:  # tell Claude what went wrong instead of crashing
                    print(f"[tool error] {block.name}: {e}")  # and show it to the developer too
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": f"Error: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    else:
        return "Stopped: too many steps without a final answer."

    answer = "".join(b.text for b in response.content if b.type == "text")
    if chart_paths:
        answer += "\n\nChart saved to: " + ", ".join(chart_paths)
    return answer


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_calls_4wk.csv"
    question = sys.argv[2] if len(sys.argv) > 2 else "Which hours of the day get the most calls?"
    print(run_agent(question, path))
