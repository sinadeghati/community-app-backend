from django.contrib.auth.models import User
from rest_framework import serializers

from listings.models import Listing

from .models import ContentReport, Event


REPORT_REASONS = frozenset(
    {
        "child_safety",
        "nudity_or_sexual_content",
        "harassment_or_abuse",
        "hate_or_discrimination",
        "spam_or_scam",
        "violence_or_dangerous_content",
        "illegal_activity",
        "other",
    }
)

TARGET_TYPE_ALIASES = {
    "user": ContentReport.ObjectType.USER,
    "profile": ContentReport.ObjectType.USER,
    "business": ContentReport.ObjectType.LISTING,
    "listing": ContentReport.ObjectType.LISTING,
    "event": ContentReport.ObjectType.EVENT,
}

CANONICAL_TARGET_TYPES = {
    ContentReport.ObjectType.USER: "user",
    ContentReport.ObjectType.LISTING: "listing",
    ContentReport.ObjectType.EVENT: "event",
}


class ContentReportCreateSerializer(serializers.Serializer):
    target_type = serializers.CharField(max_length=32)
    target_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=100)
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="",
    )

    def validate_target_type(self, value):
        normalized = value.strip().lower()
        if normalized not in TARGET_TYPE_ALIASES:
            raise serializers.ValidationError("Invalid target type.")
        return normalized

    def validate_reason(self, value):
        normalized = value.strip().lower()
        if normalized not in REPORT_REASONS:
            raise serializers.ValidationError("Invalid report reason.")
        return normalized

    def validate(self, attrs):
        object_type = TARGET_TYPE_ALIASES[attrs["target_type"]]
        target_id = attrs["target_id"]
        reporter = self.context["request"].user

        if object_type == ContentReport.ObjectType.USER:
            target = User.objects.filter(pk=target_id).first()
            if target is None:
                raise serializers.ValidationError({"target_id": "User not found."})
            if target.pk == reporter.pk:
                raise serializers.ValidationError(
                    {"target_id": "You cannot report your own account."}
                )
            attrs["resolved_object_type"] = object_type
            attrs["resolved_target"] = target
            attrs["reported_user"] = target
            attrs["listing"] = None
            attrs["event"] = None
        elif object_type == ContentReport.ObjectType.LISTING:
            target = Listing.objects.filter(pk=target_id).first()
            if target is None:
                raise serializers.ValidationError({"target_id": "Listing not found."})
            attrs["resolved_object_type"] = object_type
            attrs["resolved_target"] = target
            attrs["listing"] = target
            attrs["event"] = None
            attrs["reported_user"] = target.effective_owner
        else:
            target = Event.objects.filter(pk=target_id).first()
            if target is None:
                raise serializers.ValidationError({"target_id": "Event not found."})
            attrs["resolved_object_type"] = object_type
            attrs["resolved_target"] = target
            attrs["event"] = target
            attrs["listing"] = None
            attrs["reported_user"] = target.owner

        open_report = ContentReport.objects.filter(
            reported_by=reporter,
            reported_object_type=object_type,
            reported_object_id=target_id,
            status__in=[
                ContentReport.Status.NEW,
                ContentReport.Status.IN_REVIEW,
            ],
        ).exists()
        if open_report:
            raise serializers.ValidationError(
                {"detail": "You already have an open report for this content."}
            )

        return attrs

    def create(self, validated_data):
        target = validated_data["resolved_target"]
        object_type = validated_data["resolved_object_type"]
        report = ContentReport.objects.create(
            reported_object_type=object_type,
            reported_object_id=target.pk,
            reported_user=validated_data.get("reported_user"),
            listing=validated_data.get("listing"),
            event=validated_data.get("event"),
            reason=validated_data["reason"],
            description=validated_data.get("description", ""),
            reported_by=self.context["request"].user,
            status=ContentReport.Status.NEW,
        )
        return report


class ContentReportCreateResponseSerializer(serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()
    target_id = serializers.IntegerField(source="reported_object_id")

    class Meta:
        model = ContentReport
        fields = [
            "id",
            "target_type",
            "target_id",
            "reason",
            "status",
            "created_at",
        ]
        read_only_fields = fields

    def get_target_type(self, obj):
        return CANONICAL_TARGET_TYPES.get(
            obj.reported_object_type,
            obj.reported_object_type,
        )
