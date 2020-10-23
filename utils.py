import time


async def with_ratelimit(client, method, *args):
    response = await getattr(client, method, *args)
    if getattr(response, "status_code", None) == "M_LIMIT_EXCEEDED":
        time.sleep(3)
        return with_ratelimit(client, method, *args)
    return response
