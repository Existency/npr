from shortuuid import ShortUUID


def uuid() -> str:
    """
    Returns a short uuid (4 bytes long).

    :return: A short uuid.
    """
    return str(ShortUUID().random(length=4))
