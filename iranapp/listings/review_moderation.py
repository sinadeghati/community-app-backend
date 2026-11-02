from listings.models import BusinessReview


REVIEW_MODERATION_STATUSES = {
    "hide": BusinessReview.Status.HIDDEN,
    "remove": BusinessReview.Status.REMOVED,
    "restore": BusinessReview.Status.APPROVED,
}


def moderate_review(review, action):
    if action not in REVIEW_MODERATION_STATUSES:
        raise ValueError(f"Unknown review moderation action: {action}")
    review.status = REVIEW_MODERATION_STATUSES[action]
    review.save(update_fields=["status", "updated_at"])
    return review
