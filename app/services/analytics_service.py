import calendar
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics import AnalyticsRepository, TransactionFilter, month_bounds
from app.schemas.analytics import (
    CategoriesResponse,
    CategoryHistoryItem,
    CategoryHistoryResponse,
    CategoryMonth,
    CategoryChange,
    CategoryItem,
    CategoryRef,
    ChangesResponse,
    CitiesResponse,
    CityItem,
    ComparePreset,
    ComparisonInfo,
    CurrenciesResponse,
    CurrencyItem,
    DailyPoint,
    Insight,
    InsightAction,
    InsightsResponse,
    MerchantItem,
    MerchantsResponse,
    MonthlyResponse,
    MonthTotal,
    OtherShare,
    PeriodInfo,
    PlaceSpendItem,
    PlacesResponse,
    RecurringItem,
    RecurringResponse,
    SpendingResponse,
)
from app.core.currencies import alpha_code
from app.services.merchant_key import build_merchant_key

EXPENSE_KINDS = ("expense",)
DEFAULT_PERIOD_DAYS = 30
MAX_PERIOD_DAYS = 3 * 366
SCALED_PRESETS = {"last_3_months": 3, "last_6_months": 6, "last_year": 12}
MIN_CHANGE_AMOUNT = 20_000
MIN_GROWTH_STREAK = 2
INSIGHT_WINDOW_MONTHS = 6
MAX_INSIGHTS = 3
EQUAL_TOLERANCE = 0.01
MIN_RECURRING_MONTHS = 2
STABLE_AMOUNT_SPREAD = 0.15
STABLE_PAYMENTS_SHARE = 0.7

MONTH_LOCATIVE = (
    "січні", "лютому", "березні", "квітні", "травні", "червні",
    "липні", "серпні", "вересні", "жовтні", "листопаді", "грудні",
)
ORDINALS = {
    2: "другий", 3: "третій", 4: "четвертий", 5: "п'ятий", 6: "шостий", 7: "сьомий",
    8: "восьмий", 9: "дев'ятий", 10: "десятий", 11: "одинадцятий",
}


class PeriodError(ValueError):
    pass


@dataclass(frozen=True)
class Period:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def info(self) -> PeriodInfo:
        return PeriodInfo(start=self.start, end=self.end, days=self.days)


@dataclass(frozen=True)
class Comparison:
    type: str
    period: Period
    scaled: bool


@dataclass
class DayRow:
    month: str
    day: int
    category: CategoryRef
    spent: int


def parse_month(value: str) -> date:
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def month_key(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def add_months(day: date, months: int) -> date:
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def month_end(month: date) -> date:
    return month.replace(day=calendar.monthrange(month.year, month.month)[1])


def is_full_month(period: Period) -> bool:
    return period.start.day == 1 and period.end == month_end(period.start)


def change_pct(current: int, baseline: int) -> float | None:
    if baseline <= 0:
        return None
    return round((current - baseline) / baseline * 100, 1)


def share(amount: int, total: int) -> float:
    return round(amount / total * 100, 1) if total > 0 else 0.0


def format_uah(kopecks: int) -> str:
    return f"{round(kopecks / 100):,}".replace(",", " ") + " ₴"


def is_stable(amounts: list[int], typical: int) -> bool:
    if typical <= 0:
        return False
    close = sum(1 for amount in amounts if abs(amount - typical) <= typical * STABLE_AMOUNT_SPREAD)
    return close / len(amounts) >= STABLE_PAYMENTS_SHARE


def growth_streak(values: list[int]) -> int:
    streak = 0
    for i in range(len(values) - 1, 0, -1):
        if values[i] <= values[i - 1]:
            break
        streak += 1
    return streak


def resolve_period(today: date, month: str | None, date_from: date | None, date_to: date | None) -> Period:
    if month and (date_from or date_to):
        raise PeriodError("Use either month or from/to, not both")
    if (date_from is None) != (date_to is None):
        raise PeriodError("from and to must be given together")

    if month:
        start = parse_month(month)
        end = month_end(start)
    elif date_from is not None:
        if date_from > date_to:
            raise PeriodError("from must not be after to")
        start, end = date_from, date_to
    else:
        start, end = today - timedelta(days=DEFAULT_PERIOD_DAYS - 1), today

    if start > today:
        raise PeriodError("The period is in the future")
    period = Period(start, min(end, today))
    if period.days > MAX_PERIOD_DAYS:
        raise PeriodError(f"The period can't be longer than {MAX_PERIOD_DAYS} days")
    return period


def resolve_comparison(
    period: Period, preset: ComparePreset, compare_from: date | None, compare_to: date | None,
) -> Comparison:
    if (compare_from is None) != (compare_to is None):
        raise PeriodError("compare_from and compare_to must be given together")
    if compare_from is not None:
        if compare_from > compare_to:
            raise PeriodError("compare_from must not be after compare_to")
        return Comparison("custom", Period(compare_from, compare_to), scaled=True)

    if preset in SCALED_PRESETS:
        end = period.start - timedelta(days=1)
        return Comparison(preset, Period(add_months(period.start, -SCALED_PRESETS[preset]), end), scaled=True)

    if preset == "previous_period":
        end = period.start - timedelta(days=1)
        return Comparison(preset, Period(end - timedelta(days=period.days - 1), end), scaled=False)

    months_back = -1 if preset == "previous_month" else -12
    start = add_months(period.start, months_back)
    end = month_end(start) if is_full_month(period) else add_months(period.end, months_back)
    return Comparison(preset, Period(start, end), scaled=False)


class AnalyticsService:

    def __init__(
        self, db: AsyncSession, user_id: int, timezone: str, account_ids: list[int] | None = None,
        place_ids: list[int] | None = None, cities: list[str] | None = None,
    ):
        self.repo = AnalyticsRepository(db)
        self.user_id = user_id
        self.timezone = timezone
        self.account_ids = account_ids
        self.place_ids = place_ids
        self.city_names = cities
        self.today = datetime.now(ZoneInfo(timezone)).date()
        self.current_month = self.today.replace(day=1)
        self._history_start: date | None = None
        self._history_loaded = False

    async def spending(self, period: Period, comparison: Comparison) -> SpendingResponse:
        rows = await self._aggregate(period, ["day"])
        per_day = {row["day"]: -row["sum"] for row in rows}
        total = max(sum(per_day.values()), 0)
        comparison_info = await self._comparison_info(period, comparison)

        daily = []
        running = 0
        for offset in range(period.days):
            day = period.start + timedelta(days=offset)
            running += per_day.get(day.isoformat(), 0)
            daily.append(DailyPoint(date=day, amount=running))

        return SpendingResponse(
            period=period.info(),
            total=total,
            comparison=comparison_info,
            change_pct=change_pct(total, comparison_info.expected),
            daily=daily,
        )

    async def categories(
        self, period: Period, comparison: Comparison, top: int | None, sort: str,
    ) -> CategoriesResponse:
        totals = await self._aggregate(period, [])
        total = max(-totals[0]["sum"], 0) if totals else 0
        current = await self._category_totals(period)
        expected = await self._expected_by_category(period, comparison)

        items = [
            CategoryItem(
                category_id=category.id,
                name=category.name,
                slug=category.slug,
                amount=amount,
                share=share(amount, total),
                transaction_count=count,
                expected=expected.get(category.id, 0),
                change_pct=change_pct(amount, expected.get(category.id, 0)),
            )
            for category, amount, count in current
        ]
        if sort == "count":
            items.sort(key=lambda item: (-item.transaction_count, -item.amount))
        elif sort == "change":
            items.sort(key=lambda item: -(item.amount - item.expected))

        other = None
        if top is not None:
            items = items[:top]
            other_amount = max(total - sum(item.amount for item in items), 0)
            other = OtherShare(amount=other_amount, share=share(other_amount, total))

        return CategoriesResponse(
            period=period.info(),
            total=total,
            transaction_count=totals[0]["count"] if totals else 0,
            comparison=await self._comparison_info(period, comparison),
            items=items,
            other=other,
        )

    async def merchants(self, period: Period, limit: int, offset: int) -> MerchantsResponse:
        date_from, date_to = self._bounds(period)
        transactions = await self.repo.list_transactions(
            self.user_id,
            self._filter(date_from, date_to),
            self.timezone,
        )

        groups: dict[str, list[dict]] = defaultdict(list)
        for transaction in transactions:
            key = build_merchant_key(transaction["description"]) or transaction["description"].strip().lower()
            groups[key].append(transaction)

        merchants = []
        for key, items in groups.items():
            amount = -sum(item["amount_uah"] for item in items)
            if amount <= 0:
                continue
            category_id, category_name, category_slug = Counter(
                (item["category_id"], item["category_name"], item["category_slug"]) for item in items
            ).most_common(1)[0][0]
            merchants.append(MerchantItem(
                merchant_key=key,
                name=Counter(item["description"].strip() for item in items).most_common(1)[0][0],
                purchase_count=sum(1 for item in items if item["amount_uah"] < 0),
                amount=amount,
                category=CategoryRef(id=category_id, name=category_name, slug=category_slug),
            ))
        merchants.sort(key=lambda merchant: (-merchant.amount, merchant.name))

        return MerchantsResponse(
            period=period.info(),
            total=len(merchants),
            limit=limit,
            offset=offset,
            items=merchants[offset:offset + limit],
        )

    async def changes(self, period: Period, comparison: Comparison, limit: int) -> ChangesResponse:
        current = {category.id: (category, amount) for category, amount, _ in await self._category_totals(period)}
        expected = await self._expected_by_category(period, comparison)
        names = await self._category_refs(comparison.period)

        changes = []
        for category_id in current.keys() | expected.keys():
            category = current[category_id][0] if category_id in current else names[category_id]
            amount = current.get(category_id, (None, 0))[1]
            baseline = expected.get(category_id, 0)
            if max(amount, baseline) < MIN_CHANGE_AMOUNT or amount == baseline:
                continue
            changes.append(CategoryChange(
                category_id=category.id,
                name=category.name,
                slug=category.slug,
                amount=amount,
                expected=baseline,
                change_pct=change_pct(amount, baseline),
            ))

        changes.sort(key=lambda change: -abs(change.amount - change.expected))
        changes = changes[:limit]
        changes.sort(key=lambda change: -(change.change_pct if change.change_pct is not None else float("inf")))

        return ChangesResponse(
            period=period.info(),
            comparison=await self._comparison_info(period, comparison),
            items=changes,
        )

    async def monthly(self, month: date, months: int) -> MonthlyResponse:
        window = [add_months(month, offset) for offset in range(-(months - 1), 1)]
        rows = await self._day_rows(window[0], month)
        monthly = await self._month_totals(window, rows)
        cap_day = self._cap_day(month)

        complete = [item for item in monthly if item.complete]
        average = round(statistics.mean(item.total for item in complete)) if complete else None

        selected = monthly[-1]
        selected_vs_average = None
        if complete and selected.has_data:
            if cap_day is not None:
                baseline = statistics.mean(self._sum(rows, item.month, upto_day=cap_day) for item in complete)
                selected_vs_average = self._versus(selected.total, baseline)
            elif selected.complete:
                selected_vs_average = self._versus(selected.total, average)

        return MonthlyResponse(
            month=month_key(month),
            months=monthly,
            average=average,
            selected_vs_average=selected_vs_average,
        )

    async def insights(self, month: date) -> InsightsResponse:
        window = [add_months(month, offset) for offset in range(-(INSIGHT_WINDOW_MONTHS - 1), 1)]
        rows = await self._day_rows(window[0], month)
        monthly = await self._month_totals(window, rows)
        if not monthly[-1].has_data:
            return InsightsResponse(month=month_key(month), items=[])

        eligible = []
        for item in reversed(monthly[:-1]):
            if not item.complete:
                break
            eligible.insert(0, item.month)
        if not eligible:
            return InsightsResponse(month=month_key(month), items=[])

        cap_day = self._cap_day(month)
        series_months = [*eligible, month_key(month)]
        categories = {row.category.id: row.category for row in rows if row.month == month_key(month)}

        insights = []
        for category_id, category in categories.items():
            values = [self._sum(rows, m, category_id=category_id, upto_day=cap_day) for m in series_months]
            streak = growth_streak(values)
            if streak < MIN_GROWTH_STREAK:
                continue
            current = values[-1]
            baseline = round(statistics.median(values[:-1]))
            diff = current - baseline
            if diff < MIN_CHANGE_AMOUNT:
                continue
            title, text = self._growth_text(category.name, streak, month, current, diff, cap_day is not None)
            insights.append(Insight(
                type="category_growth_streak",
                category_id=category_id,
                category_name=category.name,
                title=title,
                text=text,
                streak_months=streak,
                current=current,
                baseline=baseline,
                diff=diff,
                action=InsightAction(type="open_transactions", category_id=category_id, month=month_key(month)),
            ))
        insights.sort(key=lambda insight: -insight.diff)
        return InsightsResponse(month=month_key(month), items=insights[:MAX_INSIGHTS])

    async def category_history(self, month: date, months: int) -> CategoryHistoryResponse:
        window = [add_months(month, offset) for offset in range(-(months - 1), 1)]
        rows = await self._day_rows(window[0], month)
        totals = await self._month_totals(window, rows)
        complete = [item.month for item in totals if item.complete]
        categories = {row.category.id: row.category for row in rows}

        items = []
        for category_id, category in categories.items():
            amounts = [CategoryMonth(month=item.month, amount=self._sum(rows, item.month, category_id)) for item in totals]
            base = [amount.amount for amount in amounts if amount.month in complete]
            items.append(CategoryHistoryItem(
                category_id=category.id,
                name=category.name,
                slug=category.slug,
                months=amounts,
                median=round(statistics.median(base)) if base else 0,
                average=round(statistics.mean(base)) if base else 0,
                active_months=sum(1 for amount in base if amount > 0),
            ))
        items.sort(key=lambda item: (-item.median, -item.average, item.name))
        return CategoryHistoryResponse(month=month_key(month), months=totals, items=items)

    async def recurring(
        self, month: date, months: int, limit: int, category_ids: list[int] | None = None,
    ) -> RecurringResponse:
        window = [month_key(add_months(month, offset)) for offset in range(-(months - 1), 1)]
        date_from, _ = month_bounds(parse_month(window[0]), self.timezone)
        _, date_to = month_bounds(month, self.timezone)
        transactions = await self.repo.list_transactions(
            self.user_id,
            self._filter(date_from, date_to, category_ids=category_ids),
            self.timezone,
        )

        zone = ZoneInfo(self.timezone)
        groups: dict[str, list[dict]] = defaultdict(list)
        for transaction in transactions:
            if transaction["amount_uah"] >= 0:
                continue
            key = build_merchant_key(transaction["description"]) or transaction["description"].strip().lower()
            groups[key].append({**transaction, "day": datetime.fromtimestamp(transaction["time"], zone).date()})

        items = []
        for key, payments in groups.items():
            by_month: dict[str, int] = defaultdict(int)
            for payment in payments:
                by_month[month_key(payment["day"])] -= payment["amount_uah"]
            if len(by_month) < MIN_RECURRING_MONTHS:
                continue
            amounts = [-payment["amount_uah"] for payment in payments]
            typical = round(statistics.median(amounts))
            category_id, category_name, category_slug = Counter(
                (payment["category_id"], payment["category_name"], payment["category_slug"]) for payment in payments
            ).most_common(1)[0][0]
            items.append(RecurringItem(
                merchant_key=key,
                name=Counter(payment["description"].strip() for payment in payments).most_common(1)[0][0],
                category=CategoryRef(id=category_id, name=category_name, slug=category_slug),
                months_seen=len(by_month),
                payment_count=len(payments),
                typical_amount=typical,
                monthly_amount=round(statistics.median(by_month.values())),
                stable_amount=is_stable(amounts, typical),
                last_date=max(payment["day"] for payment in payments),
            ))
        items.sort(key=lambda item: (-item.monthly_amount, -item.months_seen, item.name))
        return RecurringResponse(months=window, items=items[:limit])

    async def currencies(self, period: Period) -> CurrenciesResponse:
        date_from, date_to = self._bounds(period)
        rows = await self.repo.aggregate(
            self.user_id,
            self._filter(date_from, date_to),
            self.timezone,
            group_by=["currency"],
            metrics=["sum", "count", "operation_sum"],
        )
        spent = [(row, -row["sum"]) for row in rows if row["sum"] < 0]
        total = sum(amount_uah for _, amount_uah in spent)
        items = [
            CurrencyItem(
                currency=alpha_code(row["currency_code"]),
                transaction_count=row["count"],
                amount=-row["operation_sum"],
                amount_uah=amount_uah,
                share=share(amount_uah, total),
            )
            for row, amount_uah in spent
        ]
        items.sort(key=lambda item: -item.amount_uah)
        return CurrenciesResponse(period=period.info(), total_uah=total, items=items)

    async def places(self, period: Period, limit: int, offset: int) -> PlacesResponse:
        total, rows = await self._located(period, "place")
        items = [
            PlaceSpendItem(
                place_id=row["place_id"],
                name=row["place_name"],
                type_name=row["place_type"],
                city=row["place_city"],
                amount=-row["sum"],
                transaction_count=row["count"],
                share=share(-row["sum"], total),
            )
            for row in rows
        ]
        items.sort(key=lambda item: (-item.amount, item.name))
        return PlacesResponse(
            period=period.info(),
            total=total,
            unlocated_amount=max(total - sum(item.amount for item in items), 0),
            place_count=len(items),
            limit=limit,
            offset=offset,
            items=items[offset:offset + limit],
        )

    async def cities(self, period: Period) -> CitiesResponse:
        total, rows = await self._located(period, "city")
        items = [
            CityItem(city=row["city"], amount=-row["sum"], transaction_count=row["count"], share=share(-row["sum"], total))
            for row in rows
        ]
        items.sort(key=lambda item: (-item.amount, item.city))
        return CitiesResponse(
            period=period.info(),
            total=total,
            unlocated_amount=max(total - sum(item.amount for item in items), 0),
            items=items,
        )

    async def _located(self, period: Period, dimension: str) -> tuple[int, list[dict]]:
        totals = await self._aggregate(period, [])
        total = max(-totals[0]["sum"], 0) if totals else 0
        rows = await self._aggregate(period, [dimension])
        key = "place_id" if dimension == "place" else "city"
        return total, [row for row in rows if row[key] is not None and -row["sum"] > 0]

    async def _aggregate(self, period: Period, group_by: list) -> list[dict]:
        date_from, date_to = self._bounds(period)
        return await self.repo.aggregate(
            self.user_id,
            self._filter(date_from, date_to),
            self.timezone,
            group_by=group_by,
            metrics=["sum", "count"],
        )

    async def _category_totals(self, period: Period) -> list[tuple[CategoryRef, int, int]]:
        rows = await self._aggregate(period, ["category"])
        items = [
            (CategoryRef(id=row["category_id"], name=row["category_name"], slug=row["category_slug"]), -row["sum"], row["count"])
            for row in rows
            if -row["sum"] > 0
        ]
        items.sort(key=lambda item: (-item[1], item[0].name))
        return items

    async def _category_refs(self, period: Period) -> dict[int, CategoryRef]:
        return {category.id: category for category, _, _ in await self._category_totals(period)}

    async def _expected_by_category(self, period: Period, comparison: Comparison) -> dict[int, int]:
        factor = self._scale(period, comparison)
        return {
            category.id: round(amount * factor)
            for category, amount, _ in await self._category_totals(comparison.period)
        }

    async def _comparison_info(self, period: Period, comparison: Comparison) -> ComparisonInfo:
        totals = await self._aggregate(comparison.period, [])
        baseline_total = max(-totals[0]["sum"], 0) if totals else 0
        history_start = await self._get_history_start()
        return ComparisonInfo(
            type=comparison.type,
            start=comparison.period.start,
            end=comparison.period.end,
            days=comparison.period.days,
            scaled=comparison.scaled,
            complete=history_start is not None and history_start <= comparison.period.start,
            total=baseline_total,
            expected=round(baseline_total * self._scale(period, comparison)),
        )

    async def _day_rows(self, first_month: date, last_month: date) -> list[DayRow]:
        date_from, _ = month_bounds(first_month, self.timezone)
        _, date_to = month_bounds(last_month, self.timezone)
        rows = await self.repo.aggregate(
            self.user_id,
            self._filter(date_from, date_to),
            self.timezone,
            group_by=["category", "day"],
            metrics=["sum"],
        )
        return [
            DayRow(
                month=row["day"][:7],
                day=int(row["day"][8:]),
                category=CategoryRef(id=row["category_id"], name=row["category_name"], slug=row["category_slug"]),
                spent=-row["sum"],
            )
            for row in rows
        ]

    async def _month_totals(self, window: list[date], rows: list[DayRow]) -> list[MonthTotal]:
        history_start = await self._get_history_start()
        history_month = history_start.replace(day=1) if history_start else None
        totals = []
        for month in window:
            has_data = history_month is not None and history_month <= month <= self.current_month
            complete = has_data and month != self.current_month and not (
                month == history_month and history_start.day > 1
            )
            totals.append(MonthTotal(
                month=month_key(month), total=self._sum(rows, month_key(month)), has_data=has_data, complete=complete,
            ))
        return totals

    async def _get_history_start(self) -> date | None:
        if not self._history_loaded:
            first_time = await self.repo.first_transaction_time(self.user_id)
            if first_time is not None:
                self._history_start = datetime.fromtimestamp(first_time, ZoneInfo(self.timezone)).date()
            self._history_loaded = True
        return self._history_start

    def _filter(self, date_from: int, date_to: int, **extra) -> TransactionFilter:
        return TransactionFilter(
            date_from=date_from, date_to=date_to, kinds=EXPENSE_KINDS,
            account_ids=self.account_ids, place_ids=self.place_ids, cities=self.city_names, **extra,
        )

    def _bounds(self, period: Period) -> tuple[int, int]:
        tz = ZoneInfo(self.timezone)
        start = datetime.combine(period.start, datetime.min.time(), tzinfo=tz)
        end = datetime.combine(period.end + timedelta(days=1), datetime.min.time(), tzinfo=tz)
        return int(start.timestamp()), int(end.timestamp())

    def _cap_day(self, month: date) -> int | None:
        return self.today.day if month == self.current_month else None

    @staticmethod
    def _scale(period: Period, comparison: Comparison) -> float:
        return period.days / comparison.period.days if comparison.scaled else 1.0

    @staticmethod
    def _sum(rows: list[DayRow], month: str, category_id: int | None = None, upto_day: int | None = None) -> int:
        total = sum(
            row.spent for row in rows
            if row.month == month
            and (category_id is None or row.category.id == category_id)
            and (upto_day is None or row.day <= upto_day)
        )
        return max(total, 0)

    @staticmethod
    def _growth_text(
        name: str, streak: int, month: date, current: int, diff: int, in_progress: bool,
    ) -> tuple[str, str]:
        title = f"{name} зростає {ORDINALS.get(streak, f'{streak}-й')} місяць поспіль"
        month_name = MONTH_LOCATIVE[month.month - 1]
        if in_progress:
            text = (
                f"У {month_name} це вже {format_uah(current)} — "
                f"на {format_uah(diff)} більше, ніж зазвичай на цю дату."
            )
        else:
            text = f"У {month_name} це {format_uah(current)} — на {format_uah(diff)} більше за ваш звичайний місяць."
        return title, text

    @staticmethod
    def _versus(value: float, baseline: float) -> str:
        if baseline <= 0:
            return "above" if value > 0 else "equal"
        ratio = (value - baseline) / baseline
        if abs(ratio) <= EQUAL_TOLERANCE:
            return "equal"
        return "above" if ratio > 0 else "below"
