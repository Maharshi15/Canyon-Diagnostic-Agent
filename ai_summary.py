"""Writes the executive summary with Claude.

Only aggregated findings and a few example records are sent, never the whole file.
"""
import anthropic

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


def write_summary(result, client, api_key, model):
    lines = [f"Client: {client or 'Not specified'}",
             f"Records reviewed: {result['total']}",
             f"Overall data quality score: {result['overall']} out of 100",
             "Dimension scores: " + ", ".join(f"{d['dim']} {d['score']}" for d in result["dim_scores"]),
             f"Potential duplicate clusters: {len(result['dup_groups'])}",
             "Findings:"]
    for f in result["findings"]:
        ex = "; ".join(r["desc"] for r in f["rows"][:3])
        lines.append(f"* [{f['severity']}] {f['label']}: {f['count']} records. Examples: {ex}. Recommendation: {f['rec']}")
    client_api = anthropic.Anthropic(api_key=api_key)
    msg = client_api.messages.create(model=model, max_tokens=1200, system=SYSTEM,
                                     messages=[{"role": "user", "content": "\n".join(lines)}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
