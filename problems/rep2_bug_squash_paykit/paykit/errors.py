"""Exceptions raised by paykit."""


class PaykitError(Exception):
    """Base class for every error raised by paykit."""


class GatewayError(PaykitError):
    """The gateway answered with a non-2xx HTTP status.

    ``status`` is the HTTP status code and ``body`` the decoded JSON body (or the raw
    text when the body was not JSON).
    """

    def __init__(self, status, body):
        super().__init__(f"gateway returned HTTP {status}: {body!r}")
        self.status = status
        self.body = body

    @property
    def message(self):
        if isinstance(self.body, dict):
            return self.body.get("error", {}).get("message", "")
        return str(self.body)


class SignatureError(PaykitError):
    """A webhook payload could not be verified."""
