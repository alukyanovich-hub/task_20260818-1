from rest_framework.routers import DefaultRouter

from apps.transactions.views import TransactionViewSet

router = DefaultRouter()
router.register('transactions', TransactionViewSet, basename='transaction')

urlpatterns = router.urls
