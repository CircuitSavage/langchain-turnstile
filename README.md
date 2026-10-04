<div align="center">

# langchain-turnstile

**Give a LangChain agent the ability to solve Cloudflare Turnstile.** A `BaseTool` that takes a page URL and a sitekey, calls [Peak](https://peak.fo), and hands back a token. A browsing agent that hits a Turnstile challenge gets a move to make instead of getting stuck.

<p>
  <img src="https://img.shields.io/badge/python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/langchain-core-1C3C3C?style=for-the-badge" alt="langchain-core">
  <img src="https://img.shields.io/badge/license-MIT-007EC7?style=for-the-badge" alt="MIT License">
</p>

</div>

---

An agent that browses the web eventually runs into Cloudflare Turnstile. The widget needs a token minted server-side. No fingerprint, proxy, or retry loop gets around that; it's a missing capability, not a detection problem. This package is that capability, packaged as a LangChain `Tool`: give it a URL and a sitekey, it returns a token.

The tool itself never touches a browser. It is pure request/response to the Peak API, which keeps it usable from any agent regardless of whether it's driving Playwright, Selenium, a raw HTTP client, or nothing at all. Pair it with whatever tool your agent already uses to read the DOM (to get the sitekey) and to run JS (to put the token back); see [Closing the loop](#closing-the-loop) below.

## Install

```bash
pip install langchain-turnstile
```

## Use it

```python
from langchain_turnstile import PeakTurnstileTool

tool = PeakTurnstileTool(api_key="pk_...")  # or set PEAK_API_KEY
token = tool.run({"url": "https://example.com/login", "sitekey": "0x4AAAAAAA..."})
```

Hand it to an agent like any other tool:

```python
from langchain.agents import create_agent
from langchain_turnstile import PeakTurnstileTool

agent = create_agent(llm, tools=[*your_browser_tools, PeakTurnstileTool(api_key=api_key)])
```

The agent decides when to call it, typically after a browsing tool reports it's stuck on a Cloudflare challenge. The tool's `description` is written for that: an LLM reading the tool list will reach for `solve_cloudflare_turnstile` when it sees a Turnstile widget blocking a page.

## Closing the loop

Reading the sitekey and injecting the token both happen on a live page, which is specific to whatever browser your agent drives, so this package deliberately doesn't pick one for you. `inject.py` ships the JS every other Peak wrapper package uses, so you can call it from whichever `execute_script` / `page.evaluate` your stack exposes:

```python
from langchain_turnstile import build_injection_script

page.evaluate(build_injection_script(token))          # Playwright
driver.execute_script(build_injection_script(token))  # Selenium
```

It fills every `cf-turnstile-response` field and fires the widget's `data-callback` if the page registered one, the same two places a real form submit reads from.

## Matching the exit IP

Turnstile scores the IP that submits the token. If your agent's browser runs behind a proxy, pass the same one so the token and the request line up:

```python
tool.run({"url": url, "sitekey": sitekey, "proxy": "http://user:pass@host:port"})
```

Leave `proxy` out and the tool solves through Peak's own IP pool instead. Fine for most sites, wrong for the ones that bind the token to the requesting IP.

## Errors come back as text, not exceptions

A tool-calling agent works better when a failure is something it can read and react to, rather than a crash that kills the run. `PeakTurnstileTool` returns `"ERROR: <reason>"` (bad sitekey, no balance, no key configured) instead of raising, so the agent's next step can be "try a different sitekey" rather than "the whole chain died." Call `PeakClient.solve()` directly from `langchain_turnstile.peak` if you want exceptions instead.

## Getting a key

The tool needs an API key for the solver it calls: [Peak](https://peak.fo). Turnstile solves come back in about a second, you pay only for the ones that land, and the free tier is enough to wire this up and test it end to end.

<div align="center">

For **Cloudflare Turnstile**, **Cloudflare 5s challenge**, **AWS WAF**, and **DataDome**:
<br>
<a href="https://peak.fo"><img src="https://img.shields.io/badge/Get_a_key-Peak-FF6B35?style=for-the-badge" alt="Peak"></a>
<br>
<sub>API-first · <strong>$0.35 – $1.00 / 1K</strong> · volume tiers · pay only on success · <a href="https://peak.fo">peak.fo</a></sub>

</div>

## Related

Same pattern for driving a browser directly instead of through an agent: [playwright-turnstile](https://github.com/CircuitSavage/playwright-turnstile) · [selenium-turnstile](https://github.com/CircuitSavage/selenium-turnstile) · [puppeteer-extra-plugin-turnstile](https://github.com/CircuitSavage/puppeteer-extra-plugin-turnstile) · [nodriver-turnstile](https://github.com/CircuitSavage/nodriver-turnstile) · [camoufox-turnstile](https://github.com/CircuitSavage/camoufox-turnstile).

## Notes

Use this on sites and accounts you're allowed to automate. Respect each target's Terms of Service and `robots.txt`. This is tooling for legitimate agents, testing, and public-data access. Nothing here helps with credential stuffing or abuse. Not affiliated with Cloudflare or LangChain.

## License

MIT
