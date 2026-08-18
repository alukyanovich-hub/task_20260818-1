from rest_framework import serializers

from apps.transactions.models import Transaction
from apps.transactions.services.categorizer import get_categorizer


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'external_id', 'amount', 'timestamp', 'description',
            'transaction_type', 'account_number', 'category',
            'category_source', 'created_at',
        ]
        read_only_fields = ['id', 'category', 'category_source', 'created_at']

    def create(self, validated_data):
        categorizer = get_categorizer()
        category = categorizer.categorize_batch([validated_data['description']])[validated_data['description']]
        validated_data['category'] = category
        validated_data['category_source'] = categorizer.source
        return super().create(validated_data)


class TransactionImportSerializer(serializers.Serializer):
    file = serializers.FileField(help_text='CSV file with columns: Transaction ID, Amount, '
                                            'Timestamp, Description, Transaction Type, Account Number.')


class TransactionImportResultSerializer(serializers.Serializer):
    created = serializers.IntegerField()
    skipped_duplicates = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField())
