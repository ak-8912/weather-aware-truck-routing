from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
        details = None
    else:
        message = "The request could not be processed."
        details = detail

    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "api_error"),
            "message": message,
            "details": details,
        }
    }
    return response
