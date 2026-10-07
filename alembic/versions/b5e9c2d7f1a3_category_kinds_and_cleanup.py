"""category kinds (expense/income/transfer/unknown) and category cleanup

Every category gets a kind, so income and the user's own money movements can
be told apart from spending. Income and transfer categories are added, and
expense categories that duplicate each other or can't be told apart from bank
data are folded into the one that stays (e.g. "М'ясо та птиця" -> "Продукти":
the bank only ever says "SILPO").

"Перекази" used to be filled by a hard-coded rule with everything paid via a
transfer MCC - salary, money to friends, moves between own cards. It can't be
remapped mechanically, so its AI/rule-assigned transactions are reset to
uncategorized and the sweeper re-categorizes them with the new categories.

Revision ID: b5e9c2d7f1a3
Revises: a3d7e1f4b8c2
Create Date: 2026-10-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e9c2d7f1a3'
down_revision: Union[str, Sequence[str], None] = 'a3d7e1f4b8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The full target tree, parents before children: (slug, name, parent_slug, kind).
# Existing slugs are updated in place (name, parent, kind), new ones inserted.
CATEGORIES = [
    # ---------------- expense ----------------
    ('produkty', 'Продукти', None, 'expense'),
    ('alkohol', 'Алкоголь', 'produkty', 'expense'),
    ('tiutiun', 'Тютюн', 'produkty', 'expense'),

    ('kafe-ta-restorany', 'Кафе та ресторани', None, 'expense'),
    ('restorany', 'Ресторани', 'kafe-ta-restorany', 'expense'),
    ('kafe', 'Кафе', 'kafe-ta-restorany', 'expense'),
    ('kavyarni', "Кав'ярні", 'kafe-ta-restorany', 'expense'),
    ('fastfud', 'Фастфуд', 'kafe-ta-restorany', 'expense'),
    ('dostavka-izhi', 'Доставка їжі', 'kafe-ta-restorany', 'expense'),
    ('bary-ta-paby', 'Бари та паби', 'kafe-ta-restorany', 'expense'),

    ('transport', 'Транспорт', None, 'expense'),
    ('hromadskyi-transport', 'Громадський транспорт', 'transport', 'expense'),
    ('taksi', 'Таксі', 'transport', 'expense'),
    ('karsherynh', 'Каршеринг', 'transport', 'expense'),
    ('palne', 'Пальне', 'transport', 'expense'),
    ('parkuvannia', 'Паркування', 'transport', 'expense'),
    ('platni-dorohy', 'Платні дороги', 'transport', 'expense'),

    ('avtomobil', 'Автомобіль', None, 'expense'),
    ('remont-avtomobilia', 'Ремонт автомобіля', 'avtomobil', 'expense'),
    ('avtozapchastyny', 'Автозапчастини', 'avtomobil', 'expense'),
    ('myika-avtomobilia', 'Мийка автомобіля', 'avtomobil', 'expense'),
    ('strakhuvannia-avto', 'Страхування авто', 'avtomobil', 'expense'),

    ('zhytlo', 'Житло', None, 'expense'),
    ('orenda-zhytla', 'Оренда житла', 'zhytlo', 'expense'),
    ('ipoteka', 'Іпотека', 'zhytlo', 'expense'),

    ('komunalni-posluhy', 'Комунальні послуги', None, 'expense'),
    ('elektroenerhiia', 'Електроенергія', 'komunalni-posluhy', 'expense'),
    ('haz', 'Газ', 'komunalni-posluhy', 'expense'),
    ('voda', 'Вода', 'komunalni-posluhy', 'expense'),
    ('opalennia', 'Опалення', 'komunalni-posluhy', 'expense'),
    ('internet', 'Інтернет', 'komunalni-posluhy', 'expense'),
    ('mobilnyi-zviazok', "Мобільний зв'язок", 'komunalni-posluhy', 'expense'),

    ('pobutovi-posluhy', 'Побутові послуги', None, 'expense'),
    ('prybyrannia', 'Прибирання', 'pobutovi-posluhy', 'expense'),
    ('remont-ta-obsluhovuvannia-zhytla', 'Ремонт та обслуговування житла', 'pobutovi-posluhy', 'expense'),

    ('dim-ta-interier', "Дім та інтер'єр", None, 'expense'),
    ('mebli', 'Меблі', 'dim-ta-interier', 'expense'),
    ('dekor-dlia-domu', 'Декор для дому', 'dim-ta-interier', 'expense'),

    ('tekhnika-ta-elektronika', 'Техніка та електроніка', None, 'expense'),
    ('onlain-servisy-ta-pidpysky', 'Онлайн-сервіси та підписки', None, 'expense'),
    ('knyhy', 'Книги', None, 'expense'),
    ('kantseliariia', 'Канцелярія', None, 'expense'),

    ('odiah', 'Одяг', None, 'expense'),
    ('vzuttia', 'Взуття', 'odiah', 'expense'),

    ('krasa-ta-hihiiena', 'Краса та гігієна', None, 'expense'),
    ('parfumeriia', 'Парфумерія', 'krasa-ta-hihiiena', 'expense'),

    ('tovary-dlia-ditei', 'Товари для дітей', None, 'expense'),
    ('ihrashky', 'Іграшки', 'tovary-dlia-ditei', 'expense'),

    ('tovary-dlia-tvaryn', 'Товари для тварин', None, 'expense'),
    ('veterynariia', 'Ветеринарія', 'tovary-dlia-tvaryn', 'expense'),

    ('zdorovia', "Здоров'я", None, 'expense'),
    ('apteka', 'Аптека', 'zdorovia', 'expense'),
    ('stomatolohiia', 'Стоматологія', 'zdorovia', 'expense'),
    ('medychni-posluhy', 'Медичні послуги', 'zdorovia', 'expense'),
    ('analizy-ta-diahnostyka', 'Аналізи та діагностика', 'zdorovia', 'expense'),
    ('okuliary-ta-optyka', 'Окуляри та оптика', 'zdorovia', 'expense'),

    ('sport', 'Спорт', None, 'expense'),
    ('sportzal', 'Спортзал та фітнес', 'sport', 'expense'),
    ('sportyvnyi-odiah-ta-inventar', 'Спортивний одяг та інвентар', 'sport', 'expense'),

    ('rozvahy', 'Розваги та хобі', None, 'expense'),
    ('kino', 'Кіно', 'rozvahy', 'expense'),
    ('kontserty', 'Концерти та театр', 'rozvahy', 'expense'),
    ('muzei', 'Музеї', 'rozvahy', 'expense'),
    ('ihry', 'Ігри', 'rozvahy', 'expense'),

    ('podorozhi', 'Подорожі', None, 'expense'),
    ('aviakvytky', 'Авіаквитки', 'podorozhi', 'expense'),
    ('zaliznychni-kvytky', 'Залізничні квитки', 'podorozhi', 'expense'),
    ('avtobusni-kvytky', 'Автобусні квитки', 'podorozhi', 'expense'),
    ('hoteli', 'Житло в подорожі', 'podorozhi', 'expense'),
    ('turystychni-posluhy', 'Туристичні послуги', 'podorozhi', 'expense'),

    ('osvita', 'Освіта', None, 'expense'),
    ('kursy', 'Курси', 'osvita', 'expense'),

    ('posluhy-krasy', 'Послуги краси', None, 'expense'),
    ('perukarnia', 'Перукарня', 'posluhy-krasy', 'expense'),
    ('manikiur-ta-pedykiur', 'Манікюр та педикюр', 'posluhy-krasy', 'expense'),
    ('spa-ta-masazh', 'СПА та масаж', 'posluhy-krasy', 'expense'),

    ('profesiini-servisy', 'Професійні послуги', None, 'expense'),
    ('iurydychni-posluhy', 'Юридичні послуги', 'profesiini-servisy', 'expense'),
    ('bukhhalterski-posluhy', 'Бухгалтерські послуги', 'profesiini-servisy', 'expense'),
    ('derzhavni-posluhy', 'Державні послуги', 'profesiini-servisy', 'expense'),
    ('poshta-ta-dostavka', 'Пошта та доставка', 'profesiini-servisy', 'expense'),
    ('druk-ta-kopiiuvannia', 'Друк та копіювання', 'profesiini-servisy', 'expense'),
    ('marketynh-ta-reklama', 'Маркетинг та реклама', 'profesiini-servisy', 'expense'),

    ('finansy', 'Фінансові витрати', None, 'expense'),
    ('komisii-ta-zbory', 'Комісії та збори', 'finansy', 'expense'),
    ('strakhuvannia', 'Страхування', 'finansy', 'expense'),
    ('podatky', 'Податки', 'finansy', 'expense'),

    ('podarunky-ta-blahodiinist', 'Подарунки та благодійність', None, 'expense'),
    ('podarunky', 'Подарунки', 'podarunky-ta-blahodiinist', 'expense'),
    ('blahodiinist', 'Благодійність', 'podarunky-ta-blahodiinist', 'expense'),

    ('perekazy-liudiam', 'Перекази людям', None, 'expense'),
    ('inshi-vytraty', 'Інші витрати', None, 'expense'),

    # ---------------- income ----------------
    ('zarplata', 'Зарплата', None, 'income'),
    ('pidpryiemnytstvo', 'Підприємницька діяльність', None, 'income'),
    ('perekazy-vid-liudei', 'Перекази від людей', None, 'income'),
    ('keshbek', 'Кешбек та бонуси', None, 'income'),
    ('vidsotky-ta-dyvidendy', 'Відсотки та дивіденди', None, 'income'),
    ('prodazh-rechei', 'Продаж речей', None, 'income'),
    ('derzhavni-vyplaty', 'Державні виплати', None, 'income'),
    ('inshi-dokhody', 'Інші доходи', None, 'income'),

    # ---------------- transfer ----------------
    ('rukh-koshtiv', 'Рух власних коштів', None, 'transfer'),
    ('mizh-svoimy-rakhunkamy', 'Між своїми рахунками', 'rukh-koshtiv', 'transfer'),
    ('zaoshchadzhennia', 'Банки та заощадження', 'rukh-koshtiv', 'transfer'),
    ('hroshovi-zniattia', 'Готівка', 'rukh-koshtiv', 'transfer'),
    ('popovnennia-rakhunku', 'Поповнення з інших банків', 'rukh-koshtiv', 'transfer'),
    ('obmin-valiut', 'Обмін валют', 'rukh-koshtiv', 'transfer'),
    ('kredyty', 'Отримання кредиту', 'rukh-koshtiv', 'transfer'),
    ('pohashennia-kredytu', 'Погашення кредиту', 'rukh-koshtiv', 'transfer'),
    ('investytsii', 'Інвестиції', 'rukh-koshtiv', 'transfer'),

    # ---------------- unknown ----------------
    ('nevidome', 'Невідоме', None, 'unknown'),
]

# Categories that go away -> the category that absorbs their transactions,
# mappings and budgets.
MERGES = {
    # what exactly was bought in a grocery store is invisible to the bank
    'supermarkety': 'produkty',
    'frukty-ta-ovochi': 'produkty',
    'miaso-ta-ptytsia': 'produkty',
    'ryba-ta-moreprodukty': 'produkty',
    'khlib-ta-vypichka': 'produkty',
    'molochni-produkty': 'produkty',
    'solodoshchi': 'produkty',
    'napoi': 'produkty',
    'kava-ta-chai': 'kavyarni',
    'izha-na-vynis': 'kafe',
    # one transit payment system for all of these
    'metro': 'hromadskyi-transport',
    'avtobus': 'hromadskyi-transport',
    'tramvai': 'hromadskyi-transport',
    'troleibus': 'hromadskyi-transport',
    # electronics chains sell all of it
    'pobutova-tekhnika': 'tekhnika-ta-elektronika',
    'kompiutery-ta-komplektuiuchi': 'tekhnika-ta-elektronika',
    'telefony': 'tekhnika-ta-elektronika',
    'aksesuary-dlia-tekhniky': 'tekhnika-ta-elektronika',
    'prohramne-zabezpechennia': 'onlain-servisy-ta-pidpysky',
    # duplicates
    'knyhy-ta-navchalni-materialy': 'knyhy',
    'aksesuary': 'odiah',
    'kosmetyka': 'krasa-ta-hihiiena',
    'pobutova-khimiia': 'krasa-ta-hihiiena',
    'tovary-dlia-domu': 'dim-ta-interier',
    'pobutovi-vytraty': 'dim-ta-interier',
    'fitnes-ta-ioha': 'sportzal',
    'khobi': 'rozvahy',
    'muzyka': 'rozvahy',
    'teatr': 'kontserty',
    'khostely': 'hoteli',
    'orenda-zhytla-u-podorozhi': 'hoteli',
    'repetytory': 'osvita',
    'orenda-obladnannia': 'profesiini-servisy',
    'robochi-vytraty': 'profesiini-servisy',
    'vidriadzhennia': 'profesiini-servisy',
    'bankivski-komisii': 'komisii-ta-zbory',
}

# "Перекази" is split by direction for choices a person made by hand, and
# reset for re-categorization otherwise (see module docstring).
OLD_TRANSFERS = 'perekazy'
TRANSFERS_OUT = 'perekazy-liudiam'
TRANSFERS_IN = 'perekazy-vid-liudei'


def _ids(bind) -> dict[str, int]:
    return dict(bind.execute(sa.text("SELECT slug, id FROM categories")).all())


def _move(bind, old_id: int, new_id: int) -> None:
    """Repoint everything from one category to another."""
    params = {'old': old_id, 'new': new_id}
    bind.execute(sa.text("UPDATE transactions SET category_id = :new WHERE category_id = :old"), params)
    bind.execute(
        sa.text("UPDATE merchant_category_mappings SET category_id = :new WHERE category_id = :old"), params,
    )
    # One budget per (user, category): when the user already budgets the
    # absorbing category, fold the old limit into it instead of colliding.
    bind.execute(sa.text("""
        UPDATE budgets n SET amount = n.amount + o.amount
        FROM budgets o
        WHERE o.category_id = :old AND n.category_id = :new AND n.user_id = o.user_id
    """), params)
    bind.execute(sa.text("""
        DELETE FROM budgets o USING budgets n
        WHERE o.category_id = :old AND n.category_id = :new AND n.user_id = o.user_id
    """), params)
    bind.execute(sa.text("UPDATE budgets SET category_id = :new WHERE category_id = :old"), params)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('categories', sa.Column('kind', sa.String(length=20), nullable=True))
    bind = op.get_bind()

    # 1. Bring every target category to its final name/parent/kind.
    ids = _ids(bind)
    for slug, name, parent_slug, kind in CATEGORIES:
        parent_id = ids[parent_slug] if parent_slug else None
        values = {'slug': slug, 'name': name, 'parent_id': parent_id, 'kind': kind}
        if slug in ids:
            bind.execute(sa.text("""
                UPDATE categories SET name = :name, parent_id = :parent_id, kind = :kind, is_active = true
                WHERE slug = :slug
            """), values)
        else:
            ids[slug] = bind.execute(sa.text("""
                INSERT INTO categories (name, slug, parent_id, kind, is_active)
                VALUES (:name, :slug, :parent_id, :kind, true) RETURNING id
            """), values).scalar_one()

    # 2. Fold merged categories into the ones that stay.
    for old_slug, new_slug in MERGES.items():
        if old_slug in ids:
            _move(bind, ids[old_slug], ids[new_slug])

    # 3. Split "Перекази".
    if OLD_TRANSFERS in ids:
        old_id = ids[OLD_TRANSFERS]
        # asyncpg can't infer parameter types inside CASE and sends them as
        # text, hence the explicit casts.
        bind.execute(sa.text("""
            UPDATE transactions
            SET category_id = CASE WHEN amount < 0 THEN CAST(:out AS INTEGER) ELSE CAST(:in AS INTEGER) END
            WHERE category_id = :old AND category_source = 'user'
        """), {'old': old_id, 'out': ids[TRANSFERS_OUT], 'in': ids[TRANSFERS_IN]})
        bind.execute(sa.text("""
            UPDATE transactions
            SET category_id = NULL, category_source = NULL, category_confidence = NULL, merchant_mapping_id = NULL
            WHERE category_id = :old
        """), {'old': old_id})
        bind.execute(sa.text("DELETE FROM merchant_category_mappings WHERE category_id = :old"), {'old': old_id})
        _move(bind, old_id, ids[TRANSFERS_OUT])  # only budgets are left to move

    # 4. Drop what's no longer in the tree. Nothing references them any more.
    obsolete = set(ids) - {c[0] for c in CATEGORIES}
    unexpected = obsolete - set(MERGES) - {OLD_TRANSFERS}
    if unexpected:
        raise RuntimeError(f"Categories with no target or merge rule: {sorted(unexpected)}")
    if obsolete:
        bind.execute(sa.text("DELETE FROM categories WHERE slug = ANY(:slugs)"), {'slugs': sorted(obsolete)})

    # 5. Budgets only make sense on spending.
    bind.execute(sa.text("""
        DELETE FROM budgets b USING categories c
        WHERE b.category_id = c.id AND c.kind <> 'expense'
    """))

    op.alter_column('categories', 'kind', nullable=False)
    op.create_check_constraint(
        'ck_categories_kind', 'categories', "kind IN ('expense', 'income', 'transfer', 'unknown')",
    )
    op.create_index(op.f('ix_categories_kind'), 'categories', ['kind'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Schema only: merged and deleted categories, and which transactions
    # pointed at them, are not restored.
    op.drop_index(op.f('ix_categories_kind'), table_name='categories')
    op.drop_constraint('ck_categories_kind', 'categories', type_='check')
    op.drop_column('categories', 'kind')
