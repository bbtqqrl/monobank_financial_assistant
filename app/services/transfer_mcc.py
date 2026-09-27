# MCC codes that represent money movement between the user's own means
# (card-to-card transfers, cash withdrawals, account top-ups) rather than an
# actual expense or income. Used both to keep such movements out of
# expense/income filters (selectable via type="transfer" instead) and to
# categorize them deterministically as "perekazy" without an AI call.
TRANSFER_MCC_CODES = {4829, 6010, 6011, 6050, 6051, 6532, 6533, 6536, 6537, 6538, 6540}
