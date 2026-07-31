from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .pagination import AdminPageNumberPagination
from .permissions import IsKorookStaff


class AdminAPIMixin:
  authentication_classes = [SessionAuthentication]
  permission_classes = [IsKorookStaff]
  pagination_class = AdminPageNumberPagination
  parser_classes = [JSONParser, FormParser, MultiPartParser]
