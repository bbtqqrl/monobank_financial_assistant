from app.core.currencies import alpha_code
from app.schemas.categorization import CategorizationCandidate

SYSTEM_PROMPT = """You categorize transactions of a Ukrainian Monobank user.

Each category has a kind:
- expense: money the user spent.
- income: money the user received from outside (salary, business income,
  transfers from other people, cashback, interest, sales, and any incoming
  money whose source is unknown).
- transfer: the user's own money moving - between their own cards or
  accounts, to or from their jars (savings), cash withdrawal, currency
  exchange, taking or repaying a loan, investments. Neither income nor
  expense.
- unknown: use only when nothing else fits.

Given a transaction (description, amount and direction, MCC name if known,
counterparty, hints) and a list of categories grouped by kind, choose EXACTLY
ONE category.

Return JSON only:
{"category_slug": "<slug>", "confidence": <0.0-1.0>}

Rules:
- category_slug MUST exactly match one of the provided slugs.
- An outgoing payment (expense direction) is never income.
- Money coming back from a shop or service is a refund: choose the expense
  category that the original purchase would have had. A description starting
  with "Скасування" is a cancelled purchase, so it is a refund too.
- Hints about the user's own accounts or jars are reliable facts: such
  movements are transfers.
- Money sent to or received from another private person is an expense or
  income respectively, unless hints say the counterparty is the user.
- Cash put in through a terminal (a bank's own terminal such as "Термінал mono"
  or "Термінал А-Банку", or a payment terminal network such as City24, iBox or
  EasyPay) has an unknown source (see the rule below). The cash category is
  only for withdrawing cash (outgoing money).
- Incoming money whose source you cannot determine is income: choose the
  generic "other income" category with confidence of at most 0.5. Choose a
  more specific income category (salary, transfers from people, cashback,
  interest, sales) only when the description or counterparty makes it clear.
- Choose the most specific category that fits. Choose a parent category only
  when none of its subcategories fits.
- Loans and credit products of the bank (taking a credit, repaying it) are
  transfers, not income or expense.
- If MCC name is unavailable, decide from the merchant, description, amount,
  counterparty and hints.
- Be decisive. If the merchant and the category are clearly evident, use high
  confidence (0.8-1.0). Use low confidence only when genuinely ambiguous.
- If no category is a clear fit, choose the one listed under "unknown" with
  confidence around 0.0-0.2.
- Output ONLY the JSON object, with no explanation or markdown."""

_KIND_TITLES = {
    "expense": "expense",
    "income": "income",
    "transfer": "transfer (own money moving)",
    "unknown": "unknown",
}


def build_user_prompt(
    description: str,
    mcc: int | None,
    mcc_name: str | None,
    amount: int,
    currency: int,
    operation_amount: int,
    operation_currency: int,
    counter_name: str | None,
    hints: list[str],
    candidates: list[CategorizationCandidate],
) -> str:
    direction = "outgoing" if amount < 0 else "incoming"

    lines = [f"Description: {description}"]
    if mcc is not None:
        lines.append(f"MCC: {mcc}" + (f" ({mcc_name})" if mcc_name else ""))
    lines.append(f"Amount: {amount / 100:.2f} {alpha_code(currency)} ({direction})")
    if operation_currency != currency:
        lines.append(f"Original amount: {operation_amount / 100:.2f} {alpha_code(operation_currency)}")
    if counter_name:
        lines.append(f"Counterparty: {counter_name}")
    for hint in hints:
        lines.append(f"Hint: {hint}")

    for kind, title in _KIND_TITLES.items():
        group = [c for c in candidates if c.kind == kind]
        if not group:
            continue
        lines.append("")
        lines.append(f"Categories - {title}:")
        lines.extend(
            f"- {c.slug}: {c.parent_name} / {c.name}" if c.parent_name else f"- {c.slug}: {c.name}"
            for c in group
        )

    return "\n".join(lines)
