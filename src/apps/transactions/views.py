from django.db import transaction as db_transaction
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.transactions.models import Transaction
from apps.transactions.serializers import (
    TransactionImportResultSerializer,
    TransactionImportSerializer,
    TransactionSerializer,
)
from apps.transactions.services.importer import CSVFormatError, import_transactions, parse_csv


class TransactionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    filterset_fields = ['category', 'transaction_type']

    @extend_schema(request=TransactionImportSerializer, responses=TransactionImportResultSerializer)
    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser])
    def import_csv(self, request):
        serializer = TransactionImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rows = parse_csv(serializer.validated_data['file'])
        except CSVFormatError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            result = import_transactions(rows)

        return Response(
            TransactionImportResultSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )
