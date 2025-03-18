from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "error_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "error_list"):
            detail = {"message": ", ".join(exc.messages)}
        else:
            detail = {"message": exc.message}
        exc = ValidationError(detail, code=400)
    if isinstance(exc, IntegrityError):
        detail = {"message": exc}
        exc = ValidationError(detail, code=400)
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    return response