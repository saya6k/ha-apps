# Home Assistant App: LLM Conversation Agent

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield] [![agentskills.io compatible][skills-shield]][skills-spec]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

Wyoming conversation agent backed by any OpenAI-compatible LLM (OpenAI,
OpenRouter, vLLM, LM Studio, LiteLLM, Anthropic-via-gateway, …).
Registers itself with the Home Assistant Wyoming integration so Assist
can route voice commands directly to the LLM — no Ollama or OpenAI HA
integration in the way, no `base_url` workarounds.

The agent receives transcribed user speech, fetches your exposed
entities + areas + floors from Home Assistant, builds OpenAI tool
definitions, calls the LLM with those tools, executes any tool calls
back into HA via the WebSocket API, and returns a natural-language
reply that HA passes to TTS.

See [DOCS.md](DOCS.md) for installation and option details, and
[AGENTS.md](AGENTS.md) for the design contract.

Skills follow the [agentskills.io open standard][skills-spec] — SKILL.md
files authored for this addon are portable to other agentskills.io
clients (Claude Code, Hermes Agent, Cursor, …) and vice versa. See
`wyoming_llm_agent/skills.py` for the parser.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[skills-shield]: https://img.shields.io/badge/agentskills.io-compatible-blue.svg
[skills-spec]: https://agentskills.io/specification
