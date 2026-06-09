# About / Motivation

This stack is built for a solo software engineer or solo founder working on a Windows 11 laptop who wants local-only AI for coding, email, planning, and personal data organisation. You write code all day, you deal with a flood of email and documents, your drives are a mess, and you want an AI assistant that actually helps without sending everything to the cloud.

The core problems it solves are practical ones: coding faster with context-aware autocomplete and chat inside your editor; drafting emails, cover letters, and documents without pasting sensitive text into a web form; cleaning and structuring your PC drives so you can find things again; and doing planning or analysis with an AI that can reason over your own notes and files. All of this should work the same way whether you have internet or not.

Why local AI? Four reasons. Privacy: your code, emails, and personal documents never leave your machine. Predictable cost: no per-token API bills that spike when you're debugging late at night. Offline usage: everything works on a train, a plane, or anywhere with no Wi-Fi. Control: you pick the models, you set the system prompts, you decide what runs and when. Cloud tools are great, but they shouldn't be the only option.

The architecture is intentionally light. One model backend, Ollama, serves every LLM need. One editor, VS Code with the Continue extension, handles coding assistance. One chat client, Jan (or Open WebUI), handles general conversation. Simple Python scripts handle automation, backed by Windows Task Scheduler for scheduling. No microservices, no Kubernetes, no five-figure infrastructure. Just tools that run on your laptop and talk to each other over localhost.

This project is meant to evolve gradually through phases, not ship as a full "AI OS" on day one. Phase 0 gets Ollama and your editor working. Phase 1 adds useful scripts you can schedule. Phase 2 adds RAG for your documents. Later phases bring n8n workflows, voice input, and agents. Each phase is usable on its own, so you get value immediately instead of waiting for a big-bang release.

See [Phases](phases.md) for the implementation timeline, or [Architecture](architecture.md) for how the pieces fit together.
