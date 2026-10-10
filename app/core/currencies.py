UAH = 980

ISO_ALPHA = {
    980: "UAH",
    840: "USD",
    978: "EUR",
    985: "PLN",
    826: "GBP",
    756: "CHF",
    203: "CZK",
    348: "HUF",
    946: "RON",
    975: "BGN",
    208: "DKK",
    752: "SEK",
    578: "NOK",
    124: "CAD",
    36: "AUD",
    392: "JPY",
    156: "CNY",
    949: "TRY",
    784: "AED",
    981: "GEL",
    498: "MDL",
    933: "BYN",
    376: "ILS",
    410: "KRW",
    764: "THB",
    356: "INR",
    986: "BRL",
    484: "MXN",
    702: "SGD",
    344: "HKD",
    554: "NZD",
    398: "KZT",
    51: "AMD",
    944: "AZN",
}


def alpha_code(numeric: int) -> str:
    return ISO_ALPHA.get(numeric, str(numeric))


def known_amount_uah(amount: int, operation_amount: int | None, currency: int, operation_currency: int) -> int | None:
    if currency == UAH:
        return amount
    if operation_currency == UAH and operation_amount is not None:
        return operation_amount
    return None
