from django.contrib import admin

from apps.transactions.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'external_id', 'timestamp', 'description', 'amount',
        'transaction_type', 'category', 'category_source',
    )
    list_filter = ('category', 'transaction_type', 'category_source')
    search_fields = ('external_id', 'description', 'account_number')
    ordering = ('-timestamp',)
