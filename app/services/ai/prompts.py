from app.schemas.categorization import CategorizationCandidate

SYSTEM_PROMPT = """Ти — асистент, який категоризує банківські транзакції українського користувача Monobank.

Тобі буде надано опис транзакції, код MCC (тип торгової точки), суму та (якщо є) назву контрагента.
Твоє завдання — обрати ОДНУ найбільш підходящу категорію зі списку, який тобі нададуть.

Відповідай лише JSON-об'єктом, без жодного тексту навколо, за схемою:
{"category_slug": "<slug з наведеного списку>", "confidence": <число від 0.0 до 1.0>}

Правила:
- "category_slug" МАЄ бути одним зі слагів у наданому списку категорій, написаним ТОЧНО так само, без змін і перекладу.
- "confidence" — твоя чесна впевненість у виборі: 1.0 — абсолютно точно, 0.5 — швидше за все підходить,
  0.1 — це просто здогад. НЕ завищуй впевненість. Якщо опис незрозумілий, узагальнений (наприклад містить
  лише випадкові літери/цифри без назви мерчанта) або однаково підходить під кілька категорій — став низьке значення.
- Якщо жодна категорія явно не підходить — обери "nevidome" з confidence близько 0.0–0.2.
- Відповідай ЛИШЕ JSON-об'єктом, нічого більше — без пояснень, без markdown, без тексту до чи після."""


def build_user_prompt(
    description: str,
    mcc: int,
    mcc_name: str | None,
    amount: int,
    counter_name: str | None,
    candidates: list[CategorizationCandidate],
) -> str:
    amount_str = f"{amount / 100:.2f}"
    direction = "витрата" if amount < 0 else "надходження"

    lines = [
        f"Опис транзакції: {description}",
        f"MCC: {mcc}" + (f" ({mcc_name})" if mcc_name else ""),
        f"Сума: {amount_str} ({direction})",
    ]
    if counter_name:
        lines.append(f"Контрагент: {counter_name}")

    lines.append("")
    lines.append("Доступні категорії (slug: назва):")
    lines.extend(f"- {c.slug}: {c.name}" for c in candidates)
    lines.append("")
    lines.append("Поверни JSON з обраною категорією за описаною схемою.")

    return "\n".join(lines)
