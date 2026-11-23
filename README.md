# hermes-0g-provider

A [Hermes Agent](https://hermes-agent.nousresearch.com) model provider for
[0G Private Computer](https://pc.0g.ai): every chat model 0G's router serves, sent as OpenAI chat
completions to `https://router-api.0g.ai/v1`.

## Install

```sh
hermes plugins install 0g-provider       # from the Hermes plugin catalog, once listed
export OG_API_KEY=sk-...                  # an API key from https://pc.0g.ai
hermes model                              # pick "0G Private Computer", then a model
```

Keep the key out of chat transcripts: set it in your shell or with `hermes model`, never paste it
into a conversation.

## What it does

- **Models** come from 0G's public catalog (`GET /v1/models`, no key needed), so new models
  appear without updating this plugin. If the catalog cannot be reached, the picker offers a short
  built-in list (`glm-5.3`, `glm-5.3-flash`, `deepseek-v4-pro`, `kimi-k2.6`, `0gm-1.0-35b-a3b`).
- **Context length** for each model is the catalog's.
- **Reasoning effort** is sent as `reasoning_effort` only to models whose catalog entry lists that
  parameter (others reject it). Levels clamp onto `low` / `medium` / `high`. Turning reasoning off
  sends nothing, so the model thinks as it does by default.
- Requests carry Hermes's attribution headers: `X-Title: Hermes Agent` and
  `HTTP-Referer: https://hermes-agent.nousresearch.com`.

`OG_BASE_URL` points it at another 0G router, e.g. staging (`https://router-api-staging.0g.ai/v1`).

## Disclosure

- Registers one model provider and nothing else: no tools, hooks, middleware, commands or
  background processes.
- Network: inference requests go to `router-api.0g.ai` (or `OG_BASE_URL`) through Hermes's own
  client with `OG_API_KEY`, which Hermes reads. The plugin itself makes one unauthenticated
  `GET /v1/models` per process to read the public model catalog, and retries it at most every
  10 minutes if it fails.
- Reads and writes no files; stores no credentials.

## License

MIT
