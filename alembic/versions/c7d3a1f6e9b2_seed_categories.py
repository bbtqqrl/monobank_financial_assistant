"""seed categories

Revision ID: c7d3a1f6e9b2
Revises: d1e4b6a2f3c8
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d3a1f6e9b2'
down_revision: Union[str, Sequence[str], None] = 'd1e4b6a2f3c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


categories_table = sa.table(
    'categories',
    sa.column('id', sa.Integer),
    sa.column('name', sa.String),
    sa.column('slug', sa.String),
    sa.column('parent_id', sa.Integer),
    sa.column('is_active', sa.Boolean),
)

# Категорії згруповані по батьківських розділах (name, slug, parent_slug).
# Порядок важливий: батьки йдуть перед своїми дітьми.
CATEGORIES: list[dict] = [
    {'name': 'Продукти', 'slug': 'produkty', 'parent_slug': None},
    {'name': 'Супермаркети', 'slug': 'supermarkety', 'parent_slug': 'produkty'},
    {'name': 'Фрукти та овочі', 'slug': 'frukty-ta-ovochi', 'parent_slug': 'produkty'},
    {'name': "М'ясо та птиця", 'slug': 'miaso-ta-ptytsia', 'parent_slug': 'produkty'},
    {'name': 'Риба та морепродукти', 'slug': 'ryba-ta-moreprodukty', 'parent_slug': 'produkty'},
    {'name': 'Хліб та випічка', 'slug': 'khlib-ta-vypichka', 'parent_slug': 'produkty'},
    {'name': 'Молочні продукти', 'slug': 'molochni-produkty', 'parent_slug': 'produkty'},
    {'name': 'Солодощі', 'slug': 'solodoshchi', 'parent_slug': 'produkty'},
    {'name': 'Напої', 'slug': 'napoi', 'parent_slug': 'produkty'},
    {'name': 'Алкоголь', 'slug': 'alkohol', 'parent_slug': 'produkty'},
    {'name': 'Тютюн', 'slug': 'tiutiun', 'parent_slug': 'produkty'},
    {'name': 'Кава та чай', 'slug': 'kava-ta-chai', 'parent_slug': 'produkty'},
    {'name': 'Кафе та ресторани', 'slug': 'kafe-ta-restorany', 'parent_slug': None},
    {'name': 'Доставка їжі', 'slug': 'dostavka-izhi', 'parent_slug': 'kafe-ta-restorany'},
    {'name': 'Ресторани', 'slug': 'restorany', 'parent_slug': 'kafe-ta-restorany'},
    {'name': 'Кафе', 'slug': 'kafe', 'parent_slug': 'kafe-ta-restorany'},
    {'name': 'Фастфуд', 'slug': 'fastfud', 'parent_slug': 'kafe-ta-restorany'},
    {'name': 'Бари та паби', 'slug': 'bary-ta-paby', 'parent_slug': 'kafe-ta-restorany'},
    {'name': 'Їжа на виніс', 'slug': 'izha-na-vynis', 'parent_slug': 'kafe-ta-restorany'},
    {'name': 'Транспорт', 'slug': 'transport', 'parent_slug': None},
    {'name': 'Громадський транспорт', 'slug': 'hromadskyi-transport', 'parent_slug': 'transport'},
    {'name': 'Метро', 'slug': 'metro', 'parent_slug': 'transport'},
    {'name': 'Автобус', 'slug': 'avtobus', 'parent_slug': 'transport'},
    {'name': 'Трамвай', 'slug': 'tramvai', 'parent_slug': 'transport'},
    {'name': 'Тролейбус', 'slug': 'troleibus', 'parent_slug': 'transport'},
    {'name': 'Таксі', 'slug': 'taksi', 'parent_slug': 'transport'},
    {'name': 'Каршеринг', 'slug': 'karsherynh', 'parent_slug': 'transport'},
    {'name': 'Пальне', 'slug': 'palne', 'parent_slug': 'transport'},
    {'name': 'Паркування', 'slug': 'parkuvannia', 'parent_slug': 'transport'},
    {'name': 'Платні дороги', 'slug': 'platni-dorohy', 'parent_slug': 'transport'},
    {'name': 'Автомобіль', 'slug': 'avtomobil', 'parent_slug': None},
    {'name': 'Ремонт автомобіля', 'slug': 'remont-avtomobilia', 'parent_slug': 'avtomobil'},
    {'name': 'Автозапчастини', 'slug': 'avtozapchastyny', 'parent_slug': 'avtomobil'},
    {'name': 'Мийка автомобіля', 'slug': 'myika-avtomobilia', 'parent_slug': 'avtomobil'},
    {'name': 'Страхування авто', 'slug': 'strakhuvannia-avto', 'parent_slug': 'avtomobil'},
    {'name': 'Житло', 'slug': 'zhytlo', 'parent_slug': None},
    {'name': 'Оренда житла', 'slug': 'orenda-zhytla', 'parent_slug': 'zhytlo'},
    {'name': 'Іпотека', 'slug': 'ipoteka', 'parent_slug': 'zhytlo'},
    {'name': 'Комунальні послуги', 'slug': 'komunalni-posluhy', 'parent_slug': None},
    {'name': 'Електроенергія', 'slug': 'elektroenerhiia', 'parent_slug': 'komunalni-posluhy'},
    {'name': 'Газ', 'slug': 'haz', 'parent_slug': 'komunalni-posluhy'},
    {'name': 'Вода', 'slug': 'voda', 'parent_slug': 'komunalni-posluhy'},
    {'name': 'Опалення', 'slug': 'opalennia', 'parent_slug': 'komunalni-posluhy'},
    {'name': 'Інтернет', 'slug': 'internet', 'parent_slug': 'komunalni-posluhy'},
    {'name': "Мобільний зв'язок", 'slug': 'mobilnyi-zviazok', 'parent_slug': 'komunalni-posluhy'},
    {'name': 'Побутові послуги', 'slug': 'pobutovi-posluhy', 'parent_slug': None},
    {'name': 'Прибирання', 'slug': 'prybyrannia', 'parent_slug': 'pobutovi-posluhy'},
    {'name': 'Ремонт та обслуговування житла', 'slug': 'remont-ta-obsluhovuvannia-zhytla', 'parent_slug': 'pobutovi-posluhy'},
    {'name': "Дім та інтер'єр", 'slug': 'dim-ta-interier', 'parent_slug': None},
    {'name': 'Меблі', 'slug': 'mebli', 'parent_slug': 'dim-ta-interier'},
    {'name': 'Декор для дому', 'slug': 'dekor-dlia-domu', 'parent_slug': 'dim-ta-interier'},
    {'name': 'Побутова техніка', 'slug': 'pobutova-tekhnika', 'parent_slug': 'dim-ta-interier'},
    {'name': 'Техніка та електроніка', 'slug': 'tekhnika-ta-elektronika', 'parent_slug': None},
    {'name': "Комп'ютери та комплектуючі", 'slug': 'kompiutery-ta-komplektuiuchi', 'parent_slug': 'tekhnika-ta-elektronika'},
    {'name': 'Телефони', 'slug': 'telefony', 'parent_slug': 'tekhnika-ta-elektronika'},
    {'name': 'Аксесуари для техніки', 'slug': 'aksesuary-dlia-tekhniky', 'parent_slug': 'tekhnika-ta-elektronika'},
    {'name': 'Програмне забезпечення', 'slug': 'prohramne-zabezpechennia', 'parent_slug': 'tekhnika-ta-elektronika'},
    {'name': 'Онлайн-сервіси та підписки', 'slug': 'onlain-servisy-ta-pidpysky', 'parent_slug': 'tekhnika-ta-elektronika'},
    {'name': 'Ігри', 'slug': 'ihry', 'parent_slug': 'tekhnika-ta-elektronika'},
    {'name': 'Книги', 'slug': 'knyhy', 'parent_slug': None},
    {'name': 'Канцелярія', 'slug': 'kantseliariia', 'parent_slug': None},
    {'name': 'Одяг', 'slug': 'odiah', 'parent_slug': None},
    {'name': 'Взуття', 'slug': 'vzuttia', 'parent_slug': 'odiah'},
    {'name': 'Аксесуари', 'slug': 'aksesuary', 'parent_slug': 'odiah'},
    {'name': 'Краса та гігієна', 'slug': 'krasa-ta-hihiiena', 'parent_slug': None},
    {'name': 'Косметика', 'slug': 'kosmetyka', 'parent_slug': 'krasa-ta-hihiiena'},
    {'name': 'Парфумерія', 'slug': 'parfumeriia', 'parent_slug': 'krasa-ta-hihiiena'},
    {'name': 'Побутова хімія', 'slug': 'pobutova-khimiia', 'parent_slug': 'krasa-ta-hihiiena'},
    {'name': 'Товари для дому', 'slug': 'tovary-dlia-domu', 'parent_slug': None},
    {'name': 'Товари для дітей', 'slug': 'tovary-dlia-ditei', 'parent_slug': None},
    {'name': 'Іграшки', 'slug': 'ihrashky', 'parent_slug': 'tovary-dlia-ditei'},
    {'name': 'Товари для тварин', 'slug': 'tovary-dlia-tvaryn', 'parent_slug': None},
    {'name': 'Ветеринарія', 'slug': 'veterynariia', 'parent_slug': 'tovary-dlia-tvaryn'},
    {'name': "Здоров'я", 'slug': 'zdorovia', 'parent_slug': None},
    {'name': 'Аптека', 'slug': 'apteka', 'parent_slug': 'zdorovia'},
    {'name': 'Стоматологія', 'slug': 'stomatolohiia', 'parent_slug': 'zdorovia'},
    {'name': 'Медичні послуги', 'slug': 'medychni-posluhy', 'parent_slug': 'zdorovia'},
    {'name': 'Аналізи та діагностика', 'slug': 'analizy-ta-diahnostyka', 'parent_slug': 'zdorovia'},
    {'name': 'Окуляри та оптика', 'slug': 'okuliary-ta-optyka', 'parent_slug': 'zdorovia'},
    {'name': 'Спорт', 'slug': 'sport', 'parent_slug': None},
    {'name': 'Спортзал', 'slug': 'sportzal', 'parent_slug': 'sport'},
    {'name': 'Спортивний одяг та інвентар', 'slug': 'sportyvnyi-odiah-ta-inventar', 'parent_slug': 'sport'},
    {'name': 'Хобі', 'slug': 'khobi', 'parent_slug': None},
    {'name': 'Музика', 'slug': 'muzyka', 'parent_slug': 'khobi'},
    {'name': 'Концерти', 'slug': 'kontserty', 'parent_slug': 'khobi'},
    {'name': 'Кіно', 'slug': 'kino', 'parent_slug': 'khobi'},
    {'name': 'Театр', 'slug': 'teatr', 'parent_slug': 'khobi'},
    {'name': 'Музеї', 'slug': 'muzei', 'parent_slug': 'khobi'},
    {'name': 'Розваги', 'slug': 'rozvahy', 'parent_slug': None},
    {'name': 'Подорожі', 'slug': 'podorozhi', 'parent_slug': None},
    {'name': 'Авіаквитки', 'slug': 'aviakvytky', 'parent_slug': 'podorozhi'},
    {'name': 'Залізничні квитки', 'slug': 'zaliznychni-kvytky', 'parent_slug': 'podorozhi'},
    {'name': 'Автобусні квитки', 'slug': 'avtobusni-kvytky', 'parent_slug': 'podorozhi'},
    {'name': 'Готелі', 'slug': 'hoteli', 'parent_slug': 'podorozhi'},
    {'name': 'Хостели', 'slug': 'khostely', 'parent_slug': 'podorozhi'},
    {'name': 'Оренда житла у подорожі', 'slug': 'orenda-zhytla-u-podorozhi', 'parent_slug': 'podorozhi'},
    {'name': 'Туристичні послуги', 'slug': 'turystychni-posluhy', 'parent_slug': 'podorozhi'},
    {'name': 'Освіта', 'slug': 'osvita', 'parent_slug': None},
    {'name': 'Курси', 'slug': 'kursy', 'parent_slug': 'osvita'},
    {'name': 'Книги та навчальні матеріали', 'slug': 'knyhy-ta-navchalni-materialy', 'parent_slug': 'osvita'},
    {'name': 'Репетитори', 'slug': 'repetytory', 'parent_slug': 'osvita'},
    {'name': 'Фінанси', 'slug': 'finansy', 'parent_slug': None},
    {'name': 'Банківські комісії', 'slug': 'bankivski-komisii', 'parent_slug': 'finansy'},
    {'name': 'Комісії та збори', 'slug': 'komisii-ta-zbory', 'parent_slug': 'finansy'},
    {'name': 'Кредити', 'slug': 'kredyty', 'parent_slug': 'finansy'},
    {'name': 'Погашення кредиту', 'slug': 'pohashennia-kredytu', 'parent_slug': 'finansy'},
    {'name': 'Заощадження', 'slug': 'zaoshchadzhennia', 'parent_slug': 'finansy'},
    {'name': 'Інвестиції', 'slug': 'investytsii', 'parent_slug': 'finansy'},
    {'name': 'Страхування', 'slug': 'strakhuvannia', 'parent_slug': 'finansy'},
    {'name': 'Податки', 'slug': 'podatky', 'parent_slug': 'finansy'},
    {'name': 'Перекази', 'slug': 'perekazy', 'parent_slug': 'finansy'},
    {'name': 'Грошові зняття', 'slug': 'hroshovi-zniattia', 'parent_slug': 'finansy'},
    {'name': 'Поповнення рахунку', 'slug': 'popovnennia-rakhunku', 'parent_slug': 'finansy'},
    {'name': 'Подарунки та благодійність', 'slug': 'podarunky-ta-blahodiinist', 'parent_slug': None},
    {'name': 'Подарунки', 'slug': 'podarunky', 'parent_slug': 'podarunky-ta-blahodiinist'},
    {'name': 'Благодійність', 'slug': 'blahodiinist', 'parent_slug': 'podarunky-ta-blahodiinist'},
    {'name': 'Побутові витрати', 'slug': 'pobutovi-vytraty', 'parent_slug': None},
    {'name': 'Послуги краси', 'slug': 'posluhy-krasy', 'parent_slug': None},
    {'name': 'Перукарня', 'slug': 'perukarnia', 'parent_slug': 'posluhy-krasy'},
    {'name': 'Манікюр та педикюр', 'slug': 'manikiur-ta-pedykiur', 'parent_slug': 'posluhy-krasy'},
    {'name': 'СПА та масаж', 'slug': 'spa-ta-masazh', 'parent_slug': 'posluhy-krasy'},
    {'name': 'Фітнес та йога', 'slug': 'fitnes-ta-ioha', 'parent_slug': 'posluhy-krasy'},
    {'name': 'Професійні сервіси', 'slug': 'profesiini-servisy', 'parent_slug': None},
    {'name': 'Юридичні послуги', 'slug': 'iurydychni-posluhy', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Бухгалтерські послуги', 'slug': 'bukhhalterski-posluhy', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Державні послуги', 'slug': 'derzhavni-posluhy', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Пошта та доставка', 'slug': 'poshta-ta-dostavka', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Друк та копіювання', 'slug': 'druk-ta-kopiiuvannia', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Оренда обладнання', 'slug': 'orenda-obladnannia', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Робочі витрати', 'slug': 'robochi-vytraty', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Відрядження', 'slug': 'vidriadzhennia', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Маркетинг та реклама', 'slug': 'marketynh-ta-reklama', 'parent_slug': 'profesiini-servisy'},
    {'name': 'Інші витрати', 'slug': 'inshi-vytraty', 'parent_slug': None},
    {'name': 'Невідоме', 'slug': 'nevidome', 'parent_slug': None},
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    slug_to_id: dict[str, int] = {}

    for entry in CATEGORIES:
        parent_id = slug_to_id.get(entry['parent_slug']) if entry['parent_slug'] else None
        result = bind.execute(
            categories_table.insert().values(
                name=entry['name'],
                slug=entry['slug'],
                parent_id=parent_id,
                is_active=True,
            ).returning(categories_table.c.id)
        )
        slug_to_id[entry['slug']] = result.scalar_one()


def downgrade() -> None:
    """Downgrade schema."""
    slugs = [c['slug'] for c in CATEGORIES]
    op.execute(
        categories_table.delete().where(categories_table.c.slug.in_(slugs))
    )
