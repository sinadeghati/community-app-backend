from django.urls import path

from .views import GeocodeSuggestView

urlpatterns = [
    path("suggest/", GeocodeSuggestView.as_view(), name="geocode-suggest"),
]
