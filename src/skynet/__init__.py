"""The Skynet operations engine."""

from importlib.metadata import PackageNotFoundError, version


def installed_version() -> str:
    """Return the installed package version without maintaining a second version constant."""
    try:
        return version("skynet")
    except PackageNotFoundError:
        return "unknown"
