import logging

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from listings.models import Listing

from .models import Event
from .public_views import PublicEventSerializer

logger = logging.getLogger(__name__)

EVENT_MODEL_WRITE_FIELDS = (
    "title",
    "description",
    "category",
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
)


class UserEventSerializer(PublicEventSerializer):
    status = serializers.CharField(read_only=True)

    class Meta(PublicEventSerializer.Meta):
        fields = PublicEventSerializer.Meta.fields + ["status"]


class UserEventWriteSerializer(serializers.ModelSerializer):
    event_date = serializers.DateTimeField(source="starts_at", required=False)
    eventDateIso = serializers.DateTimeField(source="starts_at", required=False, write_only=True)
    endDateIso = serializers.DateTimeField(source="ends_at", required=False, allow_null=True)
    street_address = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    business_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    listing_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    ticket_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    is_public = serializers.BooleanField(required=False, write_only=True, default=True)
    cover_image = serializers.ImageField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "category",
            "starts_at",
            "event_date",
            "eventDateIso",
            "ends_at",
            "endDateIso",
            "location",
            "address",
            "street_address",
            "city",
            "state",
            "zip_code",
            "country",
            "latitude",
            "longitude",
            "organizer",
            "ticket_url",
            "listing_id",
            "business_id",
            "is_public",
            "cover_image",
        ]
        extra_kwargs = {
            "starts_at": {"required": False},
            "title": {"required": False},
        }

    def _resolve_listing(self, listing_id):
        if listing_id in (None, ""):
            return None
        request = self.context.get("request")
        listing = Listing.objects.filter(pk=listing_id).first()
        if not listing:
            raise serializers.ValidationError({"listing_id": "Business not found."})
        if request and request.user.is_authenticated:
            if listing.owner_id != request.user.id and listing.user_id != request.user.id:
                raise serializers.ValidationError(
                    {"listing_id": "You can only link your own businesses."}
                )
        return listing

    def validate(self, attrs):
        if self.instance is None:
            title = (attrs.get("title") or "").strip()
            if not title:
                raise serializers.ValidationError({"title": "Event title is required."})
            if not attrs.get("starts_at"):
                raise serializers.ValidationError(
                    {"starts_at": "Event date and time are required."}
                )
        starts = attrs.get("starts_at") or (self.instance.starts_at if self.instance else None)
        ends = attrs.get("ends_at")
        if starts and ends and ends < starts:
            raise serializers.ValidationError(
                {"ends_at": "End date and time must be after the start."}
            )
        street = self.initial_data.get("street_address")
        if street is not None and street != "":
            if not attrs.get("address"):
                attrs["address"] = str(street).strip()
        listing_id = self.initial_data.get("business_id") or self.initial_data.get(
            "listing_id"
        )
        if listing_id not in (None, "", "null"):
            attrs["listing"] = self._resolve_listing(int(listing_id))
        ends = attrs.get("ends_at")
        if ends is None and self.initial_data.get("ends_at") in ("", None):
            attrs["ends_at"] = None
        ticket = attrs.get("ticket_url")
        if ticket is None or ticket == "":
            attrs["ticket_url"] = ""
        return attrs

    def _model_payload(self, validated_data):
        payload = {
            key: validated_data[key]
            for key in EVENT_MODEL_WRITE_FIELDS
            if key in validated_data
        }
        if payload.get("ends_at") is None:
            payload["ends_at"] = None
        return payload

    def create(self, validated_data):
        is_public = validated_data.pop("is_public", True)
        listing = validated_data.pop("listing", None)
        cover_image = validated_data.pop("cover_image", None)
        payload = self._model_payload(validated_data)
        request = self.context["request"]
        status_val = Event.Status.PUBLISHED if is_public else Event.Status.DRAFT
        event = Event.objects.create(
            owner=request.user,
            status=status_val,
            listing=listing,
            cover_image=cover_image,
            **payload,
        )
        return event

    def update(self, instance, validated_data):
        is_public = validated_data.pop("is_public", None)
        listing = validated_data.pop("listing", serializers.empty)
        cover_image = validated_data.pop("cover_image", serializers.empty)
        if listing is not serializers.empty:
            instance.listing = listing
        if cover_image is not serializers.empty:
            instance.cover_image = cover_image
        if is_public is not None:
            instance.status = (
                Event.Status.PUBLISHED if is_public else Event.Status.DRAFT
            )
        for attr, value in self._model_payload(validated_data).items():
            setattr(instance, attr, value)
        instance.save()
        return instance


def _user_may_edit_event(user, event: Event) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return event.owner_id == user.id


class PublicEventListCreateView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        qs = Event.objects.filter(status=Event.Status.PUBLISHED).order_by("-starts_at")
        serializer = PublicEventSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        try:
            serializer = UserEventWriteSerializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            event = serializer.save()
            return Response(
                UserEventSerializer(event, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception:
            logger.exception("event_create_failed user_id=%s", request.user.pk)
            return Response(
                {"detail": "Could not create event. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserEventMineListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Event.objects.filter(owner=request.user)
            .select_related("listing")
            .order_by("-updated_at")
        )
        serializer = UserEventSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class UserEventDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, event_id):
        event = get_object_or_404(Event.objects.select_related("owner"), pk=event_id)
        if event.status == Event.Status.PUBLISHED:
            return Response(
                PublicEventSerializer(event, context={"request": request}).data
            )
        if _user_may_edit_event(request.user, event):
            return Response(
                UserEventSerializer(event, context={"request": request}).data
            )
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        if not _user_may_edit_event(request.user, event):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserEventWriteSerializer(
            event,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        event = serializer.save()
        return Response(UserEventSerializer(event, context={"request": request}).data)

    def delete(self, request, event_id):
        event = Event.objects.filter(pk=event_id).first()
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _user_may_edit_event(request.user, event):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
