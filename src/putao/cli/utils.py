UNITS = ["B", "KiB", "MiB"]


def bytes_to_unit(size: int) -> str:
    """Format a human-readable representation of the size in bytes

    Args:
        size: The size in bytes.

    Returns:
        The human-readable representation.
    """

    num = float(size)

    # https://stackoverflow.com/a/1094933
    for unit in UNITS:
        if abs(num) < 1024:
            return f"{num:.2f} {unit}"

        num /= 1024

    return f"{num:.2f} GiB"
