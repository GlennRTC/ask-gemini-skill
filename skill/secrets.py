import os

_cached_key = None


class SecretError(Exception):
    """The Gemini API key could not be loaded. Never carries the key value."""


def get_gemini_api_key(ssm_client=None):
    """Return the API key, loading it once per Lambda container.

    Local dev: GEMINI_API_KEY. Lambda: GEMINI_API_KEY_PARAM holds the name of an
    SSM SecureString parameter.
    """
    global _cached_key
    if _cached_key:
        return _cached_key

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        param = os.environ.get("GEMINI_API_KEY_PARAM")
        if not param:
            raise SecretError("neither GEMINI_API_KEY nor GEMINI_API_KEY_PARAM is set")
        try:
            if ssm_client is None:
                import boto3  # provided by the Lambda runtime; lazy so local runs need not have it

                ssm_client = boto3.client("ssm")
            key = ssm_client.get_parameter(Name=param, WithDecryption=True)["Parameter"]["Value"]
        except Exception as exc:
            # Only the exception type: messages from clients can echo request details.
            raise SecretError(f"could not read SSM parameter {param}: {type(exc).__name__}") from None

    if not key:
        raise SecretError("the API key is empty")
    _cached_key = key
    return key


def clear_cache():
    global _cached_key
    _cached_key = None
