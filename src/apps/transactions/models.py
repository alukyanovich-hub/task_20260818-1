from django.db import models


class Category(models.TextChoices):
    """The 10 predefined categories required by the assessment brief."""
    GROCERIES = 'groceries', 'Groceries'
    DINING_OUT = 'dining_out', 'Dining Out'
    UTILITIES = 'utilities', 'Utilities'
    TRANSPORTATION = 'transportation', 'Transportation'
    ENTERTAINMENT = 'entertainment', 'Entertainment'
    HEALTHCARE = 'healthcare', 'Healthcare'
    SHOPPING = 'shopping', 'Shopping'
    HOUSING = 'housing', 'Housing'
    EDUCATION = 'education', 'Education'
    MISCELLANEOUS = 'miscellaneous', 'Miscellaneous'


class TransactionType(models.TextChoices):
    DEBIT = 'debit', 'Debit'
    CREDIT = 'credit', 'Credit'


class CategorySource(models.TextChoices):
    """How `category` was assigned, kept for transparency/debugging."""
    AI = 'ai', 'AI'
    RULE = 'rule', 'Rule-based fallback'
    MANUAL = 'manual', 'Manual'


class Transaction(models.Model):
    external_id = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text='Source system transaction ID (e.g. from an imported CSV). '
                   'Optional for transactions submitted directly via the API.',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField()
    description = models.CharField(max_length=255)
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    account_number = models.CharField(max_length=34)

    category = models.CharField(
        max_length=20, choices=Category.choices, blank=True, default='',
    )
    category_source = models.CharField(
        max_length=10, choices=CategorySource.choices, blank=True, default='',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f'{self.external_id or self.pk} · {self.description} · {self.amount}'
