"""Give a LangChain agent the ability to solve a Turnstile it hits.

    pip install langchain-turnstile langchain langchain-openai
    export PEAK_API_KEY=pk_xxx
    export OPENAI_API_KEY=sk_xxx
    python examples/basic_agent.py

This pairs the solver tool with a plain "fetch a page" tool so the agent
can read a sitekey off the HTML itself, call solve_cloudflare_turnstile,
then use the returned token however the rest of its flow needs it (a real
agent would likely pair this with a browser toolkit instead of fetch, so
it can also inject the token back into a live page — see inject.py).
"""

import os
import re

import httpx
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from langchain_turnstile import PeakTurnstileTool


def fetch_page(url: str) -> str:
    """Fetch a URL and return its HTML, truncated to stay small."""
    resp = httpx.get(url, timeout=20, follow_redirects=True)
    return resp.text[:4000]


def find_turnstile_sitekey(html: str) -> str:
    """Pull a Turnstile sitekey out of raw HTML, if one is present."""
    match = re.search(r'data-sitekey="([^"]+)"', html)
    return match.group(1) if match else "no sitekey found on that page"


def main() -> None:
    solver = PeakTurnstileTool(api_key=os.environ["PEAK_API_KEY"])
    llm = ChatOpenAI(model="gpt-4o-mini")
    agent = create_agent(llm, tools=[fetch_page, find_turnstile_sitekey, solver])

    result = agent.invoke(
        {
            "messages": [
                (
                    "user",
                    "Fetch https://demo.turnstile.workers.dev/, find its "
                    "Turnstile sitekey, and solve the challenge for that "
                    "URL. Tell me the token you get back.",
                )
            ]
        }
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
