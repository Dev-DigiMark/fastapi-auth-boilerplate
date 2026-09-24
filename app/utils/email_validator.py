import re

import dns.exception
import dns.resolver
from fastapi import HTTPException

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email_format(email: str) -> bool:
    """Validate the format of an email address using regex."""
    return EMAIL_REGEX.match(email) is not None


def validate_email_mx_records(domain: str):
    """
    Check that the domain can actually receive mail.

    Transient resolver problems (timeouts, unreachable nameservers) fail open,
    so a flaky network can't block every signup. Only a definitive answer that
    the domain does not exist or publishes no MX records is rejected.
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
