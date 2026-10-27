"""Read-only checks for the October 2026 TLS trust-store update."""

import json
import ssl
import sys
from importlib.metadata import version

from pip._vendor import certifi


def has_affected_root(context):
    return any(
        value == "emSign ECC Root CA - G3"
        for certificate in context.get_ca_certs()
        for attribute in certificate["subject"]
        for name, value in attribute
        if name == "commonName"
    )


result = {
    "python": sys.version.split()[0],
    "openssl": ssl.OPENSSL_VERSION,
    "pip": version("pip"),
    "pip_certifi": certifi.__version__,
    "system_trusts_affected_root": has_affected_root(ssl.create_default_context()),
    "pip_trusts_affected_root": has_affected_root(
        ssl.create_default_context(cafile=certifi.where())
    ),
}
try:
    import certifi as application_certifi
except ModuleNotFoundError:
    result["application_certifi"] = None
else:
    result["application_certifi"] = application_certifi.__version__
    result["application_trusts_affected_root"] = has_affected_root(
        ssl.create_default_context(cafile=application_certifi.where())
    )
    assert not result["application_trusts_affected_root"], result
assert tuple(map(int, result["pip"].split("."))) >= (26, 2, 2), result
assert not result["system_trusts_affected_root"], result
assert not result["pip_trusts_affected_root"], result
print(json.dumps(result, indent=2))
