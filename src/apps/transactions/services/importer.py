"""CSV import for banking transaction history.

Accepts the column layout from the assessment's sample export:
Transaction ID, Amount, Timestamp, Description, Transaction Type, Account Number.
"""
import csv
import io
from datetime import timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.transactions.models import Transaction, TransactionType
from apps.transactions.services.categorizer import get_categorizer

REQUIRED_COLUMNS = {
    'Transaction ID', 'Amount', 'Timestamp', 'Description',
    'Transaction Type', 'Account Number',
}


class CSVFormatError(ValueError):
    pass


def parse_csv(file_obj):
    raw = file_obj.read()
    decoded = raw.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))

    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise CSVFormatError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")

    return list(reader)


def _parse_row(row, row_number):
    external_id = (row.get('Transaction ID') or '').strip() or None

    try:
        amount = Decimal(row['Amount'].strip())
    except (InvalidOperation, AttributeError, KeyError):
        raise CSVFormatError(f'row {row_number}: invalid amount {row.get("Amount")!r}')

    timestamp = parse_datetime(row['Timestamp'].strip())
    if timestamp is None:
        raise CSVFormatError(f'row {row_number}: invalid timestamp {row.get("Timestamp")!r}')
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp, dt_timezone.utc)

    transaction_type = row['Transaction Type'].strip().lower()
    if transaction_type not in TransactionType.values:
        raise CSVFormatError(f'row {row_number}: invalid transaction type {row.get("Transaction Type")!r}')

    description = row['Description'].strip()
    account_number = row['Account Number'].strip()

    return {
        'external_id': external_id,
        'amount': amount,
        'timestamp': timestamp,
        'description': description,
        'transaction_type': transaction_type,
        'account_number': account_number,
    }


def import_transactions(rows):
    """Parse, deduplicate, categorise and bulk-create transactions.

    Returns a summary dict: created / skipped_duplicates counts and a list
    of per-row errors (row numbers are 1-indexed, header excluded).
    """
    existing_external_ids = set(
        Transaction.objects.exclude(external_id__isnull=True).values_list('external_id', flat=True)
    )

    parsed_rows = []
    errors = []
    skipped_duplicates = 0
    seen_in_file = set()

    for row_number, row in enumerate(rows, start=1):
        try:
            parsed = _parse_row(row, row_number)
        except CSVFormatError as exc:
            errors.append(str(exc))
            continue

        external_id = parsed['external_id']
        if external_id and (external_id in existing_external_ids or external_id in seen_in_file):
            skipped_duplicates += 1
            continue
        if external_id:
            seen_in_file.add(external_id)

        parsed_rows.append(parsed)

    categorizer = get_categorizer()
    unique_descriptions = {row['description'] for row in parsed_rows}
    category_by_description = categorizer.categorize_batch(unique_descriptions)

    transactions = [
        Transaction(
            **row,
            category=category_by_description[row['description']],
            category_source=categorizer.source,
        )
        for row in parsed_rows
    ]
    Transaction.objects.bulk_create(transactions)

    return {
        'created': len(transactions),
        'skipped_duplicates': skipped_duplicates,
        'errors': errors,
    }
