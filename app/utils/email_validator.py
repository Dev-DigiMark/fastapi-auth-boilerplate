import re

import dns.asyncresolver
import dns.exception
import dns.resolver
from fastapi import HTTPException

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email_format(email: str) -> bool:
    """Validate the format of an email address using regex."""
    return EMAIL_REGEX.match(email) is not None


def validate_email_mx_records(domain: str):
    """
    Sync MX check used by Pydantic validators (which are sync).

    Transient resolver problems fail open so flaky DNS cannot block every signup.
    """
    try:
        answers = dns.resolver.resolve(domain, "MX")
    except dns.resolver.NXDOMAIN:
        raise HTTPException(
            status_code=400, detail=f"The domain '{domain}' does not exist."
        )
    except (dns.resolver.NoAnswer, dns.resolver.NoMetaqueries):
        raise HTTPException(
            status_code=400,
            detail=f"The domain '{domain}' cannot receive email.",
        )
    except dns.exception.DNSException:
        return

    if not answers:
        raise HTTPException(
            status_code=400,
            detail=f"The domain '{domain}' cannot receive email.",
        )


async def avalidate_email_mx_records(domain: str):
    """Async MX check for use outside Pydantic validators."""
    try:
        answers = await dns.asyncresolver.resolve(domain, "MX")
    except dns.resolver.NXDOMAIN:
        raise HTTPException(
            status_code=400, detail=f"The domain '{domain}' does not exist."
        )
    except (dns.resolver.NoAnswer, dns.resolver.NoMetaqueries):
        raise HTTPException(
            status_code=400,
            detail=f"The domain '{domain}' cannot receive email.",
        )
    except dns.exception.DNSException:
        return

    if not answers:
        raise HTTPException(
            status_code=400,
            detail=f"The domain '{domain}' cannot receive email.",
        )
