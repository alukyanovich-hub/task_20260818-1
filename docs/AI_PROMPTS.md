# AI prompts

## Runtime categorisation prompt

Used by `OpenAICategorizer` in
`src/apps/transactions/services/categorizer.py` (`PROMPT_TEMPLATE` /
`build_prompt`), sent to the OpenAI API once per batch of **unique**
transaction descriptions (see "Trade-offs" in the README for why batching
by unique description matters).

```
You are a banking-transaction categorisation engine.

Classify each transaction description below into exactly one of these 10 categories:
Groceries, Dining Out, Utilities, Transportation, Entertainment, Healthcare, Shopping, Housing, Education, Miscellaneous.

Rules:
- Pick exactly one category per transaction, using the category name exactly as written above.
- Use "Miscellaneous" only when none of the other 9 categories clearly apply (e.g. generic bank transfers, salary payments, tax refunds, ATM withdrawals).
- Respond with ONLY a JSON object mapping each transaction description (verbatim, exactly as given) to its category name. No prose, no markdown code fences, no extra keys.

Transactions:
1. "Albert Heijn Purchase"
2. "NS Train Ticket"
...
```

The model is called via `chat.completions.create(model=OPENAI_MODEL,
response_format={"type": "json_object"}, messages=[...])`; OpenAI's JSON
mode guarantees the reply parses as JSON, so no defensive fence-stripping
is needed. Any description the model omits, or maps to a label outside
the 10 categories, falls back to `Miscellaneous` rather than failing the
whole batch. If the API call itself raises (network error, missing/
invalid key, rate limit, no billing configured, unparseable response),
the whole batch falls back to `KeywordCategorizer` and the exception is
logged — a transaction is never left uncategorised.

Provider note: the project originally targeted the Anthropic API (Claude)
since that's the tool used to build it, but switched to OpenAI because
enabling billing on the Anthropic account required identity/government
verification the reviewer couldn't complete, while an OpenAI key was
already available. The categoriser is written behind a small interface
(`categorize_batch` + `source`) specifically so this kind of swap is a
same-shaped, isolated change — see `KeywordCategorizer` /
`OpenAICategorizer` in `categorizer.py`.

## AI coding tool used to build this project

This project was built with **Claude Code** (Anthropic's agentic CLI). No
separate one-off "write me this function" prompts were used — the tool
was driven conversationally: the assessment PDF and sample CSV were
handed to the agent, which proposed a plan (`docs/PLAN.md`), asked
clarifying questions where the brief was genuinely ambiguous (e.g. which
LLM provider to standardise on, git/GitHub workflow), and then
implemented, ran, and verified each step against a live `docker compose`
stack before moving to the next one. The full session transcript is the
authoritative record of "prompts used"; this file documents the one
prompt that matters at runtime (the categorisation prompt above).
