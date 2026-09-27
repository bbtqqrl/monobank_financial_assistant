from app.schemas.categorization import CategorizationCandidate

SYSTEM_PROMPT = """You categorize Ukrainian Monobank transactions.

Given a transaction description, amount, MCC name (if available), counterparty,
and a list of categories, choose EXACTLY ONE category.

If name of the MCC is unavailable, categorize using
the merchant, description, amount, and counterparty.

Return JSON only:
{"category_slug": "<slug>", "confidence": <0.0-1.0>}

Rules:
- category_slug MUST exactly match one of the provided category slugs.
- Be decisive. If the merchant and the right category are clearly evident, use high
  confidence (0.8-1.0) - don't hedge on obvious cases.
- Only use low confidence when the merchant or category is genuinely unclear or ambiguous.
- If no category is a clear fit, use "nevidome" with confidence around 0.0-0.2.
- Always make the best available choice; do not use "nevidome" merely because MCC is missing.
- Output ONLY the JSON object, with no explanation or markdown."""

def build_user_prompt(
    description: str,
    mcc_name: str | None,
    amount: int,
    counter_name: str | None,
    candidates: list[CategorizationCandidate],
) -> str:
    amount_str = f"{amount / 100:.2f}"
    direction = "expense" if amount < 0 else "income"

    lines = [f"Description: {description}"]
    if mcc_name:
        lines.append(f"MCC category: {mcc_name}")
    lines.append(f"Amount: {amount_str} ({direction})")
    if counter_name:
        lines.append(f"Counterparty: {counter_name}")

    lines.append("")
    lines.append("Categories:")
    lines.extend(f"- {c.slug}: {c.name}" for c in candidates)

    return "\n".join(lines)
