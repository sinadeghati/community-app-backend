from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, Promotion


class PublicEventSerializer(serializers.ModelSerializer):
    event_date = serializers.DateTimeField(source="starts_at")
    image_url = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    owner_id = serializers.CharField(source="owner_id")

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "category",
            "business_category",
            "event_date",
            "starts_at",
            "ends_at",
            "location",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "latitude",
            "longitude",
            "organizer",
            "ticket_url",
            "owner_id",
            "is_featured",
            "is_sponsored",
            "image_url",
            "cover_image",
            "created_at",
            "updated_at",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None

    def get_cover_image(self, obj):
        return self.get_image_url(obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["about"] = data.get("description") or ""
        data["business_category"] = data.get("category") or ""
        return data


class PublicPromotionSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    cta_label = serializers.CharField(source="cta_text")
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "placement",
            "channel",
            "title",
            "subtitle",
            "image_url",
            "cta_label",
            "cta_link",
            "target_route",
            "target_id",
            "starts_at",
            "ends_at",
            "is_active",
            "display_priority",
            "sponsored_label",
            "hero_approved",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class PublicEventListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Event.objects.filter(status=Event.Status.PUBLISHED).order_by("-starts_at")
        serializer = PublicEventSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class PublicPromotionListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        placement = request.query_params.get("placement")
        qs = Promotion.objects.filter(
            is_active=True,
            status=Promotion.Status.ACTIVE,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        )
        if placement:
            qs = qs.filter(placement=placement)
        qs = qs.order_by("display_priority", "-created_at")
        serializer = PublicPromotionSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class PublicHeroSlidesView(PublicPromotionListView):
    def get(self, request):
        mutable = request._request.GET.copy()
        if not mutable.get("placement"):
            mutable["placement"] = Promotion.Placement.HOME_HERO
        request._request.GET = mutable
        return super().get(request)
