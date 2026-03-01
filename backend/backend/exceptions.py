from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    data = response.data

    if isinstance(data, dict):
        message = data.get("detail") or data
    elif isinstance(data, list):
        message = data
    else:
        message = "An error occurred"

    response.data = {
        "success": False,
        "message": message,
        "errors": data
    }

    return response