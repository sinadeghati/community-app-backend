from django.urls import path
from .views import ListingListCreateView

urlpatterns = [
    path('listings/', ListingListCreateView.as_view(), name='listing-list-create'),
]