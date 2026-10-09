"""Writes the executive summary with an AI (Artificial Intelligence) model.

Supports two providers, chosen by which secrets are set:
* Azure OpenAI: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
  (optional AZURE_OPENAI_API_VERSION for older resources)
* Anthropic Claude: ANTHROPIC_API_KEY, CLAUDE_MODEL

Only aggregated findings and a few example records are sent, never the whole file.
"""

SYSTEM = """You are the Canyon Diagnostic Agent of Canyon Data Labs, Ahmedabad.
Write a short executive summary of a master data diagnostic for a client's leadership.
Rules:
* Use only the numbers given. Never invent figures or business impact numbers.
* Duplicates are potential and must be validated by the business owner.
* Plain, simple English, short sentences.
* Never use hyphen or dash characters. Write "follow up", "end to end".
* Spell out each abbreviation in brackets the first time, for example ERP (Enterprise Resource Planning).
* Structure: a three line overview, the top three issues with why they matter for purchasing, inventory and reporting,
  three quick wins for the next 30 days, and a closing next step: an expert consultation with Canyon to agree
  priorities and a cleansing and governance roadmap.
* Use Markdown headings and bullets. Under 300 words."""


def provider_config(get):
    """Return the provider settings found in secrets, or None. `get(name)` reads one secret."""
    endpoint, key, deployment = get("AZURE_OPENAI_ENDPOINT"), get("AZURE_OPENAI_API_KEY"), get("AZURE_OPENAI_DEPLOYMENT")
    if endpoint and key and deployment:
        return {"provider": "azure", "endpoint": endpoint.strip().rstrip("/"), "key": key.strip(),
                "deployment": deployment.strip(), "api_version": (get("AZURE_OPENAI_API_VERSION") or "").strip()}
    if get("ANTHROPIC_API_KEY") and get("CLAUDE_MODEL"):
        return {"provider": "anthropic", "key": get("ANTHROPIC_API_KEY").strip(), "model": get("CLAUDE_MODEL").strip()}
    return None


def build_prompt(result, client):
    lines = [f"Client: {client or 'Not specified'}",
             f"Records reviewed: {result['total']}",
             f"Overall data quality score: {result['overall']} out of 100",
             "Dimension scores: " + ", ".join(f"{d['dim']} {d['score']}" for d in result["dim_scores"]),
             f"Potential duplicate clusters: {len(result['dup_groups'])}",
             "Findings:"]
    for f in result["findings"]:
        ex = "; ".join(r["desc"] for r in f["rows"][:3])
        lines.append(f"* [{f['severity']}] {f['label']}: {f['count']} records. Examples: {ex}. Recommendation: {f['rec']}")
    return "\n".join(lines)


def _azure(cfg, prompt):
    from openai import AzureOpenAI, OpenAI, BadRequestError
    endpoint = cfg["endpoint"]
    for suffix in ("/openai/v1", "/openai"):
        if endpoint.endswith(suffix):
            endpoint = endpoint[: -len(suffix)]
    if cfg["api_version"]:
        client = AzureOpenAI(azure_endpoint=endpoint, api_key=cfg["key"], api_version=cfg["api_version"])
    else:
        client = OpenAI(base_url=endpoint + "/openai/v1/", api_key=cfg["key"])
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    try:
        resp = client.chat.completions.create(model=cfg["deployment"], messages=messages, max_completion_tokens=4000)
    except BadRequestError as e:
        if "max_completion_tokens" not in str(e):
            raise
        resp = client.chat.completions.create(model=cfg["deployment"], messages=messages, max_tokens=1500)
    return resp.choices[0].message.content or ""


def _anthropic(cfg, prompt):
    import anthropic
    msg = anthropic.Anthropic(api_key=cfg["key"]).messages.create(
        model=cfg["model"], max_tokens=1200, system=SYSTEM, messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def ask(cfg, system, prompt, max_tokens=4000, json_mode=False):
    """General call used by other modules: one system prompt, one user prompt, text back."""
    if cfg["provider"] != "azure":
        import anthropic
        msg = anthropic.Anthropic(api_key=cfg["key"]).messages.create(
            model=cfg["model"], max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    from openai import AzureOpenAI, OpenAI, BadRequestError
    endpoint = cfg["endpoint"]
    for suffix in ("/openai/v1", "/openai"):
        if endpoint.endswith(suffix):
            endpoint = endpoint[: -len(suffix)]
    if cfg["api_version"]:
        client = AzureOpenAI(azure_endpoint=endpoint, api_key=cfg["key"], api_version=cfg["api_version"])
    else:
        client = OpenAI(base_url=endpoint + "/openai/v1/", api_key=cfg["key"])
    kwargs = {"model": cfg["deployment"], "max_completion_tokens": max(max_tokens, 8000),
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    for _ in range(3):
        try:
            return client.chat.completions.create(**kwargs).choices[0].message.content or ""
        except BadRequestError as e:
            if "response_format" in str(e) and "response_format" in kwargs:
                kwargs.pop("response_format")
            elif "max_completion_tokens" in str(e) and "max_completion_tokens" in kwargs:
                kwargs.pop("max_completion_tokens")
                kwargs["max_tokens"] = max_tokens
            else:
                raise
    raise RuntimeError("The AI service rejected the request settings.")


def write_summary(result, client, cfg):
    prompt = build_prompt(result, client)
    text = _azure(cfg, prompt) if cfg["provider"] == "azure" else _anthropic(cfg, prompt)
    if not text.strip():
        raise RuntimeError("The model returned an empty answer. Try again, or use a larger deployment.")
    return text
