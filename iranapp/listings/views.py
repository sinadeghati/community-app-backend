from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets

from .categories import BUSINESS_CATEGORIES
from .models import Listing
from .serializers import ListingSerializer, ListingImageSerializer




class ListingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ListingSerializer

    def get_queryset(self):
        if self.action in ["list", "retrieve"]:
            return (
                Listing.objects.filter(status=Listing.Status.PUBLISHED)
                .order_by("-created_at")
            )
        return Listing.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="categories")
    def categories(self, request):
        return Response(
            [{"value": value, "label": value} for value in BUSINESS_CATEGORIES]
        )

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="images",
        parser_classes=[MultiPartParser, FormParser],
    )
    
    def images(self, request, pk=None):
        print("FILES:", request.FILES)
        print("DATA:", request.data)

        listing = self.get_object()

        # GET: لیست عکس‌های این listing
        if request.method == "GET":
            qs = listing.images.all()
            ser = ListingImageSerializer(qs, many=True, context={"request": request})
            return Response(ser.data)

        # POST: آپلود عکس جدید برای listing
        ser = ListingImageSerializer(data=request.data, context={"request": request})

        print("SER VALID:", ser.is_valid())
        print("SER ERRORS:", ser.errors)

        if ser.is_valid():
            obj = ser.save(listing=listing)

            print("SAVED IMAGE NAME:", getattr(obj.image, "name", None))
            print("SAVED IMAGE URL:", getattr(obj, "image_url", None))

            out = ListingImageSerializer(obj, context={"request": request}).data
            return Response(out, status=status.HTTP_201_CREATED)

        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)



class MyListingsViewSet(ModelViewSet):
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        return Listing.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

