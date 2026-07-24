import os


def is_configured():
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
    )


def get_langfuse_client():
    if not is_configured():
        return None

    try:
        from langfuse import get_client

        return get_client()
    except Exception:
        return None


def flush_langfuse():
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        pass
