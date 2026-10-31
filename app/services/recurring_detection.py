import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

SUBSCRIPTION = "subscription"
REGULAR = "regular"

SUBSCRIPTION_MCCS = {4816, 4899, 5734, 5815, 5817, 5818, 5968, 7372}
SUBSCRIPTION_CATEGORY_SLUGS = {"onlain-servisy-ta-pidpysky"}
REGULAR_CATEGORY_SLUGS = {"internet", "mobilnyi-zviazok"}
NOT_REGULAR_CATEGORY_SLUGS = {
    "produkty", "kafe-ta-restorany", "odiah", "marketpleisy", "tekhnika-ta-elektronika", "dim-ta-interier",
    "podorozhi", "taksi", "hromadskyi-transport", "palne", "karsherynh", "ihry", "perekazy-liudiam",
}

AMOUNT_TOLERANCE = 0.15
SUBSCRIPTION_AMOUNT_TOLERANCE = 0.02
SUBSCRIPTION_MIN_GAP_DAYS = 28
SUBSCRIPTION_MAX_GAP_DAYS = 35
SIMILAR_SHARE = 0.7
MAX_CHARGES_PER_MONTH = 2
PRICE_CHANGE_WINDOW_DAYS = 5
PRICE_CHANGE_MAX_RATIO = 1.5
DEFAULT_PERIOD_DAYS = 30
MAX_REGULAR_PERIOD_DAYS = 70
DAYS_PER_MONTH = 30.4
GRACE_DAYS = 7
DAY_SECONDS = 24 * 3600
KYIV_TZ = ZoneInfo("Europe/Kyiv")


@dataclass(frozen=True)
class Charge:
    transaction_id: int
    time: int
    merchant_key: str
    description: str
    mcc: int | None
    category_id: int | None
    category_slug: str | None
    parent_slug: str | None
    currency_code: int
    amount: int
    amount_uah: int
    recurring_payment_id: int | None = None


@dataclass
class Cluster:
    merchant_key: str
    currency_code: int
    charges: list[Charge] = field(default_factory=list)

    @property
    def last(self) -> Charge:
        return self.charges[-1]

    @property
    def period_days(self) -> int:
        gaps = [(b.time - a.time) / DAY_SECONDS for a, b in zip(self.charges, self.charges[1:])]
        return max(1, round(statistics.median(gaps))) if gaps else DEFAULT_PERIOD_DAYS

    @property
    def name(self) -> str:
        return Counter(charge.description.strip() for charge in self.charges).most_common(1)[0][0]

    @property
    def mcc(self) -> int | None:
        return Counter(charge.mcc for charge in self.charges).most_common(1)[0][0]

    @property
    def category_id(self) -> int | None:
        return Counter(charge.category_id for charge in self.charges).most_common(1)[0][0]

    @property
    def slugs(self) -> set[str]:
        return _slugs(self.charges)


def _slugs(charges: list[Charge]) -> set[str]:
    slug, parent = Counter((charge.category_slug, charge.parent_slug) for charge in charges).most_common(1)[0][0]
    return {s for s in (slug, parent) if s}


def similar(a: int, b: int, tolerance: float = AMOUNT_TOLERANCE) -> bool:
    return abs(a - b) <= tolerance * max(a, b)


def _price_change(clusters: list[Cluster], charge: Charge) -> Cluster | None:
    deviations = [
        (abs((charge.time - cluster.last.time) / DAY_SECONDS - cluster.period_days), cluster)
        for cluster in clusters
        if max(charge.amount, cluster.last.amount) <= PRICE_CHANGE_MAX_RATIO * min(charge.amount, cluster.last.amount)
    ]
    deviations = [(deviation, cluster) for deviation, cluster in deviations if deviation <= PRICE_CHANGE_WINDOW_DAYS]
    return min(deviations, key=lambda item: item[0])[1] if deviations else None


def cluster_charges(charges: list[Charge]) -> list[Cluster]:
    groups: dict[tuple[str, int], list[Charge]] = defaultdict(list)
    for charge in sorted(charges, key=lambda c: (c.time, c.transaction_id)):
        groups[(charge.merchant_key, charge.currency_code)].append(charge)

    clusters = []
    for (merchant_key, currency_code), items in groups.items():
        if _slugs(items) & REGULAR_CATEGORY_SLUGS:
            clusters.append(Cluster(merchant_key, currency_code, items))
            continue
        own: list[Cluster] = []
        for charge in items:
            target = next((c for c in own if similar(c.last.amount, charge.amount)), None) or _price_change(own, charge)
            if target is None:
                own.append(Cluster(merchant_key, currency_code, [charge]))
            else:
                target.charges.append(charge)
        clusters.extend(own)
    return clusters


def is_whole_merchant(cluster: Cluster) -> bool:
    return bool(cluster.slugs & REGULAR_CATEGORY_SLUGS)


def is_subscription_merchant(mcc: int | None, slugs: set[str]) -> bool:
    if slugs & REGULAR_CATEGORY_SLUGS:
        return False
    return mcc in SUBSCRIPTION_MCCS or bool(slugs & SUBSCRIPTION_CATEGORY_SLUGS)


def subscription_merchant(cluster: Cluster) -> bool:
    return is_subscription_merchant(cluster.mcc, cluster.slugs)


def has_monthly_rhythm(cluster: Cluster) -> bool:
    return any(
        similar(a.amount, b.amount, SUBSCRIPTION_AMOUNT_TOLERANCE)
        and SUBSCRIPTION_MIN_GAP_DAYS * DAY_SECONDS <= b.time - a.time <= SUBSCRIPTION_MAX_GAP_DAYS * DAY_SECONDS
        for a, b in zip(cluster.charges, cluster.charges[1:])
    )


def _month_index(timestamp: int) -> int:
    moment = datetime.fromtimestamp(timestamp, KYIV_TZ)
    return moment.year * 12 + moment.month


def regular_eligible(cluster: Cluster) -> bool:
    slugs = cluster.slugs
    if slugs & NOT_REGULAR_CATEGORY_SLUGS:
        return False
    months = {_month_index(charge.time) for charge in cluster.charges}
    if len(months) < 2:
        return False
    span = max(months) - min(months) + 1
    if len(cluster.charges) > MAX_CHARGES_PER_MONTH * span or cluster.period_days > MAX_REGULAR_PERIOD_DAYS:
        return False
    if slugs & REGULAR_CATEGORY_SLUGS:
        return True
    typical = statistics.median(charge.amount for charge in cluster.charges)
    close = sum(1 for charge in cluster.charges if similar(charge.amount, typical))
    return close >= SIMILAR_SHARE * len(cluster.charges)


# TODO: річні підписки поки не ловимо
def detect_kind(cluster: Cluster, declined_kind: str | None = None) -> str | None:
    if declined_kind == REGULAR:
        return None
    if subscription_merchant(cluster) and declined_kind != SUBSCRIPTION:
        return SUBSCRIPTION if has_monthly_rhythm(cluster) else None
    if regular_eligible(cluster):
        return REGULAR
    return None


def typical_amounts(cluster: Cluster, kind: str | None) -> tuple[int, int]:
    if kind == SUBSCRIPTION:
        return cluster.last.amount, cluster.last.amount_uah
    recent = cluster.charges[-3:]
    return (
        round(statistics.median(charge.amount for charge in recent)),
        round(statistics.median(charge.amount_uah for charge in recent)),
    )


def payment_state(last_charge_at: int, period_days: int, kind: str | None, now: int, confirmed: bool = False) -> str:
    if kind == SUBSCRIPTION:
        period_days, grace_days = SUBSCRIPTION_MAX_GAP_DAYS, 0
    else:
        grace_days = GRACE_DAYS
    due = last_charge_at + (period_days + grace_days) * DAY_SECONDS
    if now <= due:
        return "active"
    if confirmed or now <= due + period_days * DAY_SECONDS:
        return "missing"
    return "inactive"


def monthly_amount(amount: int, period_days: int) -> int:
    return round(amount / max(1, round(period_days / DAYS_PER_MONTH)))
