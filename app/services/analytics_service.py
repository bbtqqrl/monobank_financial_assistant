import calendar
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics import AnalyticsRepository, TransactionFilter, month_bounds
from app.schemas.analytics import (
    CategoriesResponse,
    CategoryBreakdown,
    CategoryChange,
    CategoryItem,
    CategoryRef,
    CategoryShare,
    DailyPoint,
    Insight,
    InsightAction,
    MerchantItem,
    MerchantsResponse,
    MonthTotal,
    OtherShare,
    SummaryResponse,
    TrendsResponse,
)
from app.services.merchant_key import build_merchant_key

EXPENSE_KINDS = ("expense",)
MIN_CHANGE_AMOUNT = 20_000
MAX_CHANGES = 4
MAX_INSIGHTS = 3
MIN_GROWTH_STREAK = 2
TOP_MERCHANTS = 3
EQUAL_TOLERANCE = 0.01

MONTH_LOCATIVE = (
    "січні", "лютому", "березні", "квітні", "травні", "червні",
    "липні", "серпні", "вересні", "жовтні", "листопаді", "грудні",
)
ORDINALS = {
    2: "другий", 3: "третій", 4: "четвертий", 5: "п'ятий", 6: "шостий", 7: "сьомий",
    8: "восьмий", 9: "дев'ятий", 10: "десятий", 11: "одинадцятий",
}


def parse_month(value: str) -> date:
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def month_key(month: date) -> str:
    return f"{month.year:04d}-{month.month:02d}"


def shift_month(month: date, delta: int) -> date:
    index = month.year * 12 + month.month - 1 + delta
    return date(index // 12, index % 12 + 1, 1)


def change_pct(current: int, previous: int) -> float | None:
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def share(amount: int, total: int) -> float:
    return round(amount / total * 100, 1) if total > 0 else 0.0


def format_uah(kopecks: int) -> str:
    return f"{round(kopecks / 100):,}".replace(",", " ") + " ₴"


def growth_streak(values: list[int]) -> int:
    streak = 0
    for i in range(len(values) - 1, 0, -1):
        if values[i] <= values[i - 1]:
            break
        streak += 1
    return streak


@dataclass
class DayRow:
    month: str
    day: int
    category: CategoryRef
    spent: int
    count: int


class AnalyticsService:

    def __init__(self, db: AsyncSession, user_id: int, timezone: str, account_ids: list[int] | None = None):
        self.repo = AnalyticsRepository(db)
        self.user_id = user_id
        self.timezone = timezone
        self.account_ids = account_ids
        today = datetime.now(ZoneInfo(timezone)).date()
        self.today = today
        self.current_month = date(today.year, today.month, 1)

    def current_month_key(self) -> str:
        return month_key(self.current_month)

    async def summary(self, month: date, top: int) -> SummaryResponse:
        previous = shift_month(month, -1)
        rows = await self._day_rows(previous, month)
        cap_day = self._cap_day(month)
        current_rows = [row for row in rows if row.month == month_key(month)]

        total = self._total(current_rows)
        previous_total = self._total(rows, month_key(previous), upto_day=cap_day)
        by_category = self._by_category(current_rows)

        top_items = [
            CategoryShare(category_id=c.id, name=c.name, slug=c.slug, amount=amount, share=share(amount, total))
            for c, amount, _ in by_category[:top]
        ]
        other_amount = max(total - sum(item.amount for item in top_items), 0)

        merchants = await self._merchants(month)
        return SummaryResponse(
            month=month_key(month),
            total_spent=total,
            previous_total=previous_total,
            change_pct=change_pct(total, previous_total),
            comparison=self._comparison(month),
            daily_cumulative=self._daily_cumulative(month, current_rows),
            categories=CategoryBreakdown(
                top=top_items,
                other=OtherShare(amount=other_amount, share=share(other_amount, total)),
            ),
            top_merchants=merchants[:TOP_MERCHANTS],
        )

    async def categories(self, month: date, sort: str) -> CategoriesResponse:
        previous = shift_month(month, -1)
        rows = await self._day_rows(previous, month)
        cap_day = self._cap_day(month)
        current_rows = [row for row in rows if row.month == month_key(month)]
        previous_rows = [
            row for row in rows
            if row.month == month_key(previous) and (cap_day is None or row.day <= cap_day)
        ]

        total = self._total(current_rows)
        previous_by_id = {c.id: amount for c, amount, _ in self._by_category(previous_rows)}
        items = [
            CategoryItem(
                category_id=c.id,
                name=c.name,
                slug=c.slug,
                amount=amount,
                share=share(amount, total),
                transaction_count=count,
                previous_amount=previous_by_id.get(c.id, 0),
                change_pct=change_pct(amount, previous_by_id.get(c.id, 0)),
            )
            for c, amount, count in self._by_category(current_rows)
        ]
        if sort == "count":
            items.sort(key=lambda item: (-item.transaction_count, -item.amount))
        elif sort == "change":
            items.sort(key=lambda item: -(item.amount - item.previous_amount))

        return CategoriesResponse(
            month=month_key(month),
            transaction_count=sum(row.count for row in current_rows),
            total_spent=total,
            comparison=self._comparison(month),
            items=items,
        )

    async def merchants(self, month: date, limit: int, offset: int) -> MerchantsResponse:
        merchants = await self._merchants(month)
        return MerchantsResponse(
            month=month_key(month),
            total=len(merchants),
            limit=limit,
            offset=offset,
            items=merchants[offset:offset + limit],
        )

    async def trends(self, month: date, months: int) -> TrendsResponse:
        first = shift_month(month, -(months - 1))
        window = [shift_month(first, i) for i in range(months)]
        rows = await self._day_rows(first, month)
        history_start = await self._history_start()
        cap_day = self._cap_day(month)

        monthly = []
        for m in window:
            has_data = history_start is not None and m >= date(history_start.year, history_start.month, 1) \
                and m <= self.current_month
            complete = has_data and m != self.current_month and not (
                m == date(history_start.year, history_start.month, 1) and history_start.day > 1
            )
            monthly.append(MonthTotal(
                month=month_key(m), total=self._total(rows, month_key(m)), has_data=has_data, complete=complete,
            ))

        complete_months = [item for item in monthly if item.complete]
        average = round(statistics.mean(item.total for item in complete_months)) if complete_months else None

        selected = monthly[-1]
        selected_vs_average = None
        if complete_months and selected.has_data:
            if cap_day is not None:
                baseline = statistics.mean(
                    self._total(rows, item.month, upto_day=cap_day) for item in complete_months
                )
                selected_vs_average = self._versus(selected.total, baseline)
            elif selected.complete:
                selected_vs_average = self._versus(selected.total, average)

        return TrendsResponse(
            month=month_key(month),
            monthly=monthly,
            average=average,
            selected_vs_average=selected_vs_average,
            comparison=self._comparison(month),
            changes_vs_previous=self._changes(rows, month, cap_day),
            insights=self._insights(rows, month, monthly, cap_day) if selected.has_data else [],
        )

    async def _day_rows(self, first: date, last: date) -> list[DayRow]:
        date_from, _ = month_bounds(first, self.timezone)
        _, date_to = month_bounds(last, self.timezone)
        result = await self.repo.aggregate(
            self.user_id,
            TransactionFilter(
                date_from=date_from, date_to=date_to, kinds=EXPENSE_KINDS, account_ids=self.account_ids,
            ),
            self.timezone,
            group_by=["category", "day"],
            metrics=["sum", "count"],
        )
        return [
            DayRow(
                month=row["day"][:7],
                day=int(row["day"][8:]),
                category=CategoryRef(id=row["category_id"], name=row["category_name"], slug=row["category_slug"]),
                spent=-row["sum"],
                count=row["count"],
            )
            for row in result
        ]

    async def _merchants(self, month: date) -> list[MerchantItem]:
        date_from, date_to = month_bounds(month, self.timezone)
        transactions = await self.repo.list_transactions(
            self.user_id,
            TransactionFilter(
                date_from=date_from, date_to=date_to, kinds=EXPENSE_KINDS, account_ids=self.account_ids,
            ),
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
            categories = Counter(
                (item["category_id"], item["category_name"], item["category_slug"]) for item in items
            )
            category_id, category_name, category_slug = categories.most_common(1)[0][0]
            merchants.append(MerchantItem(
                merchant_key=key,
                name=Counter(item["description"].strip() for item in items).most_common(1)[0][0],
                purchase_count=sum(1 for item in items if item["amount_uah"] < 0),
                amount=amount,
                category=CategoryRef(id=category_id, name=category_name, slug=category_slug),
            ))
        merchants.sort(key=lambda merchant: (-merchant.amount, merchant.name))
        return merchants

    async def _history_start(self) -> date | None:
        first_time = await self.repo.first_transaction_time(self.user_id)
        if first_time is None:
            return None
        return datetime.fromtimestamp(first_time, ZoneInfo(self.timezone)).date()

    def _changes(self, rows: list[DayRow], month: date, cap_day: int | None) -> list[CategoryChange]:
        previous_key = month_key(shift_month(month, -1))
        current = {c.id: (c, amount) for c, amount, _ in self._by_category(
            [row for row in rows if row.month == month_key(month)]
        )}
        previous = {c.id: (c, amount) for c, amount, _ in self._by_category(
            [row for row in rows if row.month == previous_key and (cap_day is None or row.day <= cap_day)]
        )}

        changes = []
        for category_id in current.keys() | previous.keys():
            category = (current.get(category_id) or previous[category_id])[0]
            current_amount = current.get(category_id, (None, 0))[1]
            previous_amount = previous.get(category_id, (None, 0))[1]
            if max(current_amount, previous_amount) < MIN_CHANGE_AMOUNT or current_amount == previous_amount:
                continue
            changes.append(CategoryChange(
                category_id=category.id,
                name=category.name,
                slug=category.slug,
                current=current_amount,
                previous=previous_amount,
                change_pct=change_pct(current_amount, previous_amount),
            ))
        changes.sort(key=lambda change: -abs(change.current - change.previous))
        return changes[:MAX_CHANGES]

    def _insights(
        self, rows: list[DayRow], month: date, monthly: list[MonthTotal], cap_day: int | None,
    ) -> list[Insight]:
        eligible = []
        for item in reversed(monthly[:-1]):
            if not item.complete:
                break
            eligible.insert(0, item.month)
        if not eligible:
            return []
        series_months = [*eligible, month_key(month)]

        categories = {row.category.id: row.category for row in rows if row.month == month_key(month)}
        insights = []
        for category_id, category in categories.items():
            values = [
                self._total(rows, m, category_id=category_id, upto_day=cap_day) for m in series_months
            ]
            streak = growth_streak(values)
            if streak < MIN_GROWTH_STREAK:
                continue
            current = values[-1]
            baseline = round(statistics.median(values[:-1]))
            diff = current - baseline
            if diff < MIN_CHANGE_AMOUNT:
                continue
            insights.append(Insight(
                type="category_growth_streak",
                category_id=category_id,
                category_name=category.name,
                streak_months=streak,
                current=current,
                baseline=baseline,
                diff=diff,
                text=self._growth_text(category.name, streak, month, current, diff, cap_day is not None),
                action=InsightAction(type="open_transactions", category_id=category_id, month=month_key(month)),
            ))
        insights.sort(key=lambda insight: -insight.diff)
        return insights[:MAX_INSIGHTS]

    @staticmethod
    def _growth_text(name: str, streak: int, month: date, current: int, diff: int, in_progress: bool) -> str:
        ordinal = ORDINALS.get(streak, f"{streak}-й")
        month_name = MONTH_LOCATIVE[month.month - 1]
        if in_progress:
            return (
                f"{name} зростає {ordinal} місяць поспіль. У {month_name} це вже {format_uah(current)} — "
                f"на {format_uah(diff)} більше, ніж зазвичай на цю дату."
            )
        return (
            f"{name} зростає {ordinal} місяць поспіль. У {month_name} це {format_uah(current)} — "
            f"на {format_uah(diff)} більше за ваш звичайний місяць."
        )

    def _daily_cumulative(self, month: date, rows: list[DayRow]) -> list[DailyPoint]:
        if month > self.current_month:
            return []
        last_day = self.today.day if month == self.current_month else calendar.monthrange(month.year, month.month)[1]
        per_day = defaultdict(int)
        for row in rows:
            per_day[row.day] += row.spent

        points = []
        running = 0
        for day in range(1, last_day + 1):
            running += per_day[day]
            points.append(DailyPoint(date=f"{month_key(month)}-{day:02d}", amount=running))
        return points

    @staticmethod
    def _by_category(rows: list[DayRow]) -> list[tuple[CategoryRef, int, int]]:
        totals: dict[int, list] = {}
        for row in rows:
            entry = totals.setdefault(row.category.id, [row.category, 0, 0])
            entry[1] += row.spent
            entry[2] += row.count
        items = [(category, amount, count) for category, amount, count in totals.values() if amount > 0]
        items.sort(key=lambda item: (-item[1], item[0].name))
        return items

    @staticmethod
    def _total(
        rows: list[DayRow], month: str | None = None, category_id: int | None = None, upto_day: int | None = None,
    ) -> int:
        total = sum(
            row.spent for row in rows
            if (month is None or row.month == month)
            and (category_id is None or row.category.id == category_id)
            and (upto_day is None or row.day <= upto_day)
        )
        return max(total, 0)

    def _cap_day(self, month: date) -> int | None:
        return self.today.day if month == self.current_month else None

    def _comparison(self, month: date) -> str:
        return "same_day" if month == self.current_month else "full_month"

    @staticmethod
    def _versus(value: float, baseline: float) -> str:
        if baseline <= 0:
            return "above" if value > 0 else "equal"
        ratio = (value - baseline) / baseline
        if abs(ratio) <= EQUAL_TOLERANCE:
            return "equal"
        return "above" if ratio > 0 else "below"
