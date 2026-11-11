"""One-message test: confirms the API key, credits and install all work.

Run:  python test_api.py
The key is read from the ANTHROPIC_API_KEY environment variable. Never put it in this file.
"""
import anthropic

MODEL = "claude-sonnet-5-5"  # change here if you want to try another model

client = anthropic.Anthropic()  # finds ANTHROPIC_API_KEY on its own

reply = client.messages.create(
    model=MODEL,
    max_tokens=1000,
    messages=[{"role": "user", "content": "Reply with one short sentence confirming you can hear me."}],
)

# A reply is a list of blocks (for example thinking, then text). Print only the text ones.
text = "".join(block.text for block in reply.content if block.type == "text")
print("Claude says:", text)
print("Tokens used - input:", reply.usage.input_tokens, "output:", reply.usage.output_tokens)
