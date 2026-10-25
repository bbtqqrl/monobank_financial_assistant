import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Literal
from zoneinfo import ZoneInfo

from anthropic.types import ToolParam
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.currencies import ISO_ALPHA, UAH, alpha_code
from app.db.models.memory import MAX_MEMORY_LENGTH
from app.repositories.account import AccountRepository
from app.repositories.jar import JarRepository
from app.repositories.memory import MemoryRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.analytics import ComparePreset
from app.services.analytics_service import (
    AnalyticsService,
    Comparison,
    Period,
    PeriodError,
    parse_month,
    resolve_comparison,
    resolve_period,
)
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.errors import ServiceError

logger = logging.getLogger(__name__)

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
MAX_MEMORIES = 50
CURRENCY_CODES = {alpha: numeric for numeric, alpha in ISO_ALPHA.items()}
MONEY_KEYS = frozenset({
    "total", "total_uah", "expected", "amount", "amount_uah", "operation_amount", "current", "baseline", "diff",
    "average", "balance", "credit_limit", "goal", "current_amount", "median", "typical_amount", "monthly_amount",
})
ACCOUNT_TYPE_NAMES = {
    "black": "Чорна картка",
    "white": "Біла картка",
    "platinum": "Platinum",
    "iron": "Iron",
    "yellow": "Жовта картка",
    "fop": "Рахунок ФОП",
    "eAid": "єПідтримка",
    "madeInUkraine": "Зроблено в Україні",
}


class ToolError(Exception):
    pass


@dataclass(frozen=True)
class ToolContext:
    db: AsyncSession
    user_id: int
    timezone: str
    conversation_id: int | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    label: str
    description: str
    args: type[BaseModel]
    handler: Callable[[ToolContext, Any], Awaitable[Any]]

    def definition(self) -> ToolParam:
        return {"name": self.name, "description": self.description, "input_schema": self.args.model_json_schema()}


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PeriodArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str | None = Field(
        default=None, pattern=MONTH_PATTERN, description="Календарний місяць YYYY-MM. Не разом з date_from/date_to.",
    )
    date_from: date | None = Field(default=None, description="Початок періоду YYYY-MM-DD, тільки разом з date_to.")
    date_to: date | None = Field(default=None, description="Кінець періоду YYYY-MM-DD включно, тільки разом з date_from.")
    account_ids: list[int] | None = Field(
        default=None, description="Тільки ці рахунки (id з get_accounts). Без нього всі рахунки.",
    )


class CompareArgs(PeriodArgs):
    compare: ComparePreset | None = Field(
        default=None,
        description=(
            "З чим порівнювати. Без нього: для month - previous_month, інакше previous_period. "
            "previous_period - такий самий відрізок перед періодом; previous_month - ті самі дні минулого місяця; "
            "year_ago; last_3_months, last_6_months, last_year - середнє за цей час, приведене до довжини періоду."
        ),
    )
    compare_from: date | None = Field(
        default=None, description="Власна база порівняння: початок, разом з compare_to. Перекриває compare.",
    )
    compare_to: date | None = Field(default=None, description="Власна база порівняння: кінець включно.")


class CategoriesArgs(CompareArgs):
    top: int | None = Field(default=None, ge=1, le=50, description="Скільки категорій повернути, решта піде в other.")
    sort: Literal["amount", "count", "change"] = Field(
        default="amount", description="Сортування: за сумою, кількістю або зростанням проти бази.",
    )


class MerchantsArgs(PeriodArgs):
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


class ChangesArgs(CompareArgs):
    limit: int = Field(default=5, ge=1, le=20)


class MonthArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str | None = Field(default=None, pattern=MONTH_PATTERN, description="Місяць YYYY-MM. Без нього поточний.")
    account_ids: list[int] | None = Field(default=None, description="Тільки ці рахунки. Без нього всі.")


class MonthlyArgs(MonthArgs):
    months: int = Field(default=6, ge=2, le=12, description="Скільки місяців показати, закінчуючи month.")


class CategoryHistoryArgs(MonthlyArgs):
    category_ids: list[int] | None = Field(default=None, description="Тільки ці категорії верхнього рівня. Без нього всі.")


class RecurringArgs(MonthlyArgs):
    category_ids: list[int] | None = Field(default=None, description="Тільки ці категорії; батьківська охоплює дочірні.")
    limit: int = Field(default=20, ge=1, le=50)


class CategoryTreeArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["expense", "income", "transfer"] | None = Field(default=None, description="Тільки категорії цього типу.")


class RememberArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        min_length=1, max_length=MAX_MEMORY_LENGTH,
        description="Один факт коротким реченням від третьої особи, з цифрами і датою, якщо вони важливі.",
    )


class UpdateMemoryArgs(RememberArgs):
    id: int = Field(description="id спогаду з <memories>.")


class ForgetArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="id спогаду з <memories>.")


class SearchTransactionsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort: Literal["newest", "largest_expense"] = Field(
        default="newest", description="newest - від найновіших; largest_expense - від найбільшої витрати в гривнях.",
    )
    currency: str | None = Field(
        default=None, pattern=r"^[A-Z]{3}$",
        description=(
            "Валюта ISO, наприклад PLN або EUR: операції, де покупка була в цій валюті або картка в цій валюті."
        ),
    )
    search: str | None = Field(default=None, max_length=100, description="Підрядок в описі транзакції без урахування регістру.")
    category_id: int | None = Field(default=None, description="Категорія; батьківська охоплює дочірні.")
    type: Literal["expense", "income", "transfer"] | None = Field(
        default=None,
        description="Тип категорії. Не став, якщо шукаєш платежі конкретному мерчанту: поповнення й перекази мають тип transfer.",
    )
    date_from: date | None = Field(default=None, description="З цієї дати YYYY-MM-DD включно.")
    date_to: date | None = Field(default=None, description="По цю дату YYYY-MM-DD включно.")
    account_id: int | None = None
    jar_id: int | None = None
    limit: int = Field(default=20, ge=1, le=50)
    page: int = Field(default=1, ge=1)


def _analytics(ctx: ToolContext, account_ids: list[int] | None) -> AnalyticsService:
    return AnalyticsService(ctx.db, ctx.user_id, ctx.timezone, account_ids)


def _period(service: AnalyticsService, args: PeriodArgs) -> Period:
    return resolve_period(service.today, args.month, args.date_from, args.date_to)


def _comparison(period: Period, args: CompareArgs) -> Comparison:
    preset = args.compare or ("previous_month" if args.month else "previous_period")
    return resolve_comparison(period, preset, args.compare_from, args.compare_to)


def _month(service: AnalyticsService, month: str | None) -> date:
    selected = parse_month(month) if month else service.current_month
    if selected > service.current_month:
        raise PeriodError("The month is in the future")
    return selected


async def get_spending(ctx: ToolContext, args: CompareArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    period = _period(service, args)
    result = await service.spending(period, _comparison(period, args))
    return result.model_dump(mode="json", exclude={"daily"})


async def get_categories_breakdown(ctx: ToolContext, args: CategoriesArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    period = _period(service, args)
    result = await service.categories(period, _comparison(period, args), args.top, args.sort)
    return result.model_dump(mode="json")


async def get_merchants(ctx: ToolContext, args: MerchantsArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    result = await service.merchants(_period(service, args), args.limit, args.offset)
    data = result.model_dump(mode="json")
    data["merchant_count"] = data.pop("total")
    return data


async def get_changes(ctx: ToolContext, args: ChangesArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    period = _period(service, args)
    result = await service.changes(period, _comparison(period, args), args.limit)
    return result.model_dump(mode="json")


async def get_monthly(ctx: ToolContext, args: MonthlyArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    result = await service.monthly(_month(service, args.month), args.months)
    return result.model_dump(mode="json")


async def get_insights(ctx: ToolContext, args: MonthArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    result = await service.insights(_month(service, args.month))
    return result.model_dump(mode="json", exclude={"items": {"__all__": {"action"}}})


async def get_category_history(ctx: ToolContext, args: CategoryHistoryArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    result = await service.category_history(_month(service, args.month), args.months)
    if args.category_ids:
        result.items = [item for item in result.items if item.category_id in args.category_ids]
    return result.model_dump(mode="json")


async def get_recurring(ctx: ToolContext, args: RecurringArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    result = await service.recurring(_month(service, args.month), args.months, args.limit, args.category_ids)
    return result.model_dump(mode="json")


async def get_currency_breakdown(ctx: ToolContext, args: PeriodArgs) -> dict:
    service = _analytics(ctx, args.account_ids)
    result = await service.currencies(_period(service, args))
    return result.model_dump(mode="json")


async def get_accounts(ctx: ToolContext, args: NoArgs) -> dict:
    accounts = await AccountRepository(ctx.db).list_for_user(ctx.user_id)
    jars = await JarRepository(ctx.db).list_for_user(ctx.user_id)
    return {
        "accounts": [
            {
                "id": account.id,
                "name": ACCOUNT_TYPE_NAMES.get(account.account_type, account.account_type),
                "currency": alpha_code(account.currency_code),
                "balance": account.balance,
                "credit_limit": account.credit_limit,
                "masked_pan": account.masked_pan,
                "is_active": account.is_active,
            }
            for account in accounts
        ],
        "jars": [
            {
                "id": jar.id,
                "title": jar.title,
                "currency": alpha_code(jar.currency_code),
                "balance": jar.balance,
                "goal": jar.goal,
                "is_active": jar.is_active,
            }
            for jar in jars
        ],
    }


async def get_budgets(ctx: ToolContext, args: NoArgs) -> dict:
    budgets = await BudgetService(ctx.db, ctx.user_id).list_all()
    return {"items": [budget.model_dump(mode="json") for budget in budgets]}


async def get_category_tree(ctx: ToolContext, args: CategoryTreeArgs) -> dict:
    tree = await CategoryService(ctx.db).tree(args.kind)
    return {"items": [node.model_dump(mode="json") for node in tree]}


async def search_transactions(ctx: ToolContext, args: SearchTransactionsArgs) -> dict:
    currency_code = None
    if args.currency is not None:
        currency_code = CURRENCY_CODES.get(args.currency)
        if currency_code is None:
            raise ToolError(f"Unknown currency: {args.currency}")
    zone = ZoneInfo(ctx.timezone)
    ts_from = int(datetime.combine(args.date_from, time.min, tzinfo=zone).timestamp()) if args.date_from else None
    ts_to = int(datetime.combine(args.date_to, time.max, tzinfo=zone).timestamp()) if args.date_to else None
    rows, total = await TransactionRepository(ctx.db).list_for_user(
        user_id=ctx.user_id,
        account_id=args.account_id,
        jar_id=args.jar_id,
        category_id=args.category_id,
        type_=args.type,
        date_from=ts_from,
        date_to=ts_to,
        search=args.search,
        page=args.page,
        limit=args.limit,
        currency_code=currency_code,
        order=args.sort,
    )
    result = {
        "total_count": total,
        "page": args.page,
        "items": [_transaction_item(transaction, category, currency, zone) for transaction, category, currency in rows],
    }
    narrowing = [name for name in ("type", "currency", "category_id") if getattr(args, name) is not None]
    if total == 0 and narrowing:
        result["hint"] = (
            f"Nothing found with filters {narrowing}. Before saying there is nothing, search again without them: "
            "payments to services like Revolut are often transfers, not expenses."
        )
    return result


async def remember(ctx: ToolContext, args: RememberArgs) -> dict:
    memories = MemoryRepository(ctx.db)
    if await memories.count_for_user(ctx.user_id) >= MAX_MEMORIES:
        raise ToolError("Memory is full: update or forget an outdated memory first")
    memory = await memories.create(ctx.user_id, args.text.strip(), ctx.conversation_id)
    await ctx.db.commit()
    return {"id": memory.id, "status": "saved"}


async def update_memory(ctx: ToolContext, args: UpdateMemoryArgs) -> dict:
    memories = MemoryRepository(ctx.db)
    memory = await memories.get_for_user(args.id, ctx.user_id)
    if memory is None:
        raise ToolError(f"Memory {args.id} not found")
    memories.update(memory, args.text.strip())
    await ctx.db.commit()
    return {"id": memory.id, "status": "updated"}


async def forget(ctx: ToolContext, args: ForgetArgs) -> dict:
    memories = MemoryRepository(ctx.db)
    memory = await memories.get_for_user(args.id, ctx.user_id)
    if memory is None:
        raise ToolError(f"Memory {args.id} not found")
    await memories.delete(memory)
    await ctx.db.commit()
    return {"id": args.id, "status": "forgotten"}


def _transaction_item(transaction, category, account_currency: int, zone: ZoneInfo) -> dict:
    item = {
        "id": transaction.id,
        "time": datetime.fromtimestamp(transaction.time, zone).strftime("%Y-%m-%d %H:%M"),
        "description": transaction.description,
        "amount": transaction.amount,
        "currency": alpha_code(account_currency),
    }
    if transaction.currency_code != account_currency and transaction.operation_amount is not None:
        item["operation_amount"] = transaction.operation_amount
        item["operation_currency"] = alpha_code(transaction.currency_code)
    if account_currency != UAH:
        item["amount_uah"] = transaction.amount_uah
    item["category"] = {"id": category.id, "name": category.name} if category else None
    item["account_id"] = transaction.account_id
    item["jar_id"] = transaction.jar_id
    if transaction.comment:
        item["comment"] = transaction.comment
    return item


READ_TOOLS = (
    Tool(
        name="get_spending",
        label="Рахую витрати",
        description="Загальна сума витрат за період і порівняння з базою (expected, change_pct). Для питань «скільки я витратив».",
        args=CompareArgs,
        handler=get_spending,
    ),
    Tool(
        name="get_categories_breakdown",
        label="Розбираю витрати по категоріях",
        description="Витрати за період по категоріях верхнього рівня: сума, частка, кількість, порівняння з базою.",
        args=CategoriesArgs,
        handler=get_categories_breakdown,
    ),
    Tool(
        name="get_merchants",
        label="Шукаю, де ти витрачаєш найбільше",
        description="Мерчанти, у яких витрачено найбільше за період: сума, кількість покупок, категорія.",
        args=MerchantsArgs,
        handler=get_merchants,
    ),
    Tool(
        name="get_changes",
        label="Порівнюю з минулим",
        description="Категорії, витрати в яких найбільше змінилися проти бази порівняння.",
        args=ChangesArgs,
        handler=get_changes,
    ),
    Tool(
        name="get_monthly",
        label="Дивлюся витрати по місяцях",
        description="Сума витрат по місяцях за останні months місяців до month включно і середнє за повні місяці.",
        args=MonthlyArgs,
        handler=get_monthly,
    ),
    Tool(
        name="get_category_history",
        label="Дивлюся, як змінювались категорії",
        description=(
            "Витрати по кожній категорії верхнього рівня за кожен з months місяців до month включно. "
            "median і average рахуються лише по повних місяцях (complete); active_months - у скількох повних місяцях були витрати. "
            "Основа для «звичайного місяця», бюджетів і планів заощаджень: бери median, вона не чутлива до разових покупок."
        ),
        args=CategoryHistoryArgs,
        handler=get_category_history,
    ),
    Tool(
        name="get_recurring",
        label="Шукаю регулярні платежі",
        description=(
            "Мерчанти й люди, яким платили щонайменше у двох різних місяцях з months: підписки, сервіси, перекази тим самим людям, "
            "звичні магазини. months_seen - у скількох місяцях були платежі, typical_amount - медіана одного платежу, "
            "monthly_amount - медіана суми за місяць, stable_amount - сума майже не змінюється (схоже на підписку). "
            "Відсортовано за monthly_amount."
        ),
        args=RecurringArgs,
        handler=get_recurring,
    ),
    Tool(
        name="get_insights",
        label="Шукаю закономірності",
        description="Готові спостереження за місяць: категорії, у яких витрати ростуть кілька місяців поспіль.",
        args=MonthArgs,
        handler=get_insights,
    ),
    Tool(
        name="get_currency_breakdown",
        label="Рахую витрати по валютах",
        description=(
            "Витрати за період по валюті покупки: amount у цій валюті, amount_uah у гривнях, кількість, частка. "
            "Для питань про витрати в злотих, євро тощо і про покупки за кордоном."
        ),
        args=PeriodArgs,
        handler=get_currency_breakdown,
    ),
    Tool(
        name="get_accounts",
        label="Дивлюся рахунки",
        description="Картки і банки користувача з поточними балансами і id для фільтрів.",
        args=NoArgs,
        handler=get_accounts,
    ),
    Tool(
        name="get_budgets",
        label="Перевіряю бюджети",
        description="Місячні бюджети по категоріях: ліміт amount і скільки вже витрачено цього місяця current_amount.",
        args=NoArgs,
        handler=get_budgets,
    ),
    Tool(
        name="get_category_tree",
        label="Дивлюся категорії",
        description="Дерево категорій з id, назвами і типами. Потрібне, щоб знайти category_id.",
        args=CategoryTreeArgs,
        handler=get_category_tree,
    ),
    Tool(
        name="search_transactions",
        label="Шукаю транзакції",
        description=(
            "Окремі транзакції з фільтрами. amount у валюті рахунку currency (від'ємна - витрата). "
            "Якщо покупка була в іншій валюті, є operation_amount і operation_currency. "
            "Для сум за період краще аналітичні інструменти."
        ),
        args=SearchTransactionsArgs,
        handler=search_transactions,
    ),
)


MEMORY_TOOLS = (
    Tool(
        name="remember",
        label="Запам'ятовую",
        description=(
            "Зберегти новий факт про користувача. Якщо схожий факт уже є в <memories>, використай update_memory."
        ),
        args=RememberArgs,
        handler=remember,
    ),
    Tool(
        name="update_memory",
        label="Оновлюю те, що пам'ятаю",
        description="Замінити текст спогаду, коли факт змінився або уточнився.",
        args=UpdateMemoryArgs,
        handler=update_memory,
    ),
    Tool(
        name="forget",
        label="Забуваю",
        description="Видалити спогад, коли він більше не правда або користувач просить забути.",
        args=ForgetArgs,
        handler=forget,
    ),
)


class ToolRegistry:

    def __init__(self, tools: tuple[Tool, ...]):
        self._tools = {tool.name: tool for tool in tools}
        self._definitions = [tool.definition() for tool in tools]

    @property
    def definitions(self) -> list[ToolParam]:
        return self._definitions

    def label(self, name: str) -> str:
        tool = self._tools.get(name)
        return tool.label if tool else name

    async def run(self, ctx: ToolContext, name: str, raw_input: dict) -> tuple[str, bool]:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}", True
        try:
            args = tool.args.model_validate(raw_input)
            result = await tool.handler(ctx, args)
        except ValidationError as e:
            return f"Invalid arguments: {e.errors(include_url=False, include_context=False)}", True
        except (PeriodError, ServiceError, ToolError) as e:
            return str(e), True
        except Exception:
            logger.exception("Assistant tool %s failed", name)
            return "Internal error while running the tool", True
        return json.dumps(_to_major_units(result), ensure_ascii=False, separators=(",", ":"), default=str), False


def _to_major_units(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: round(item / 100, 2) if key in MONEY_KEYS and isinstance(item, int) else _to_major_units(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_to_major_units(item) for item in value]
    return value


READ_REGISTRY = ToolRegistry(READ_TOOLS)
MEMORY_REGISTRY = ToolRegistry(MEMORY_TOOLS)
