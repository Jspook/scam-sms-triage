"""Turn a hostname into numeric features a model can use."""


def hostname_length(host):
    return len(host)


def digit_count(host):
    return sum(ch.isdigit() for ch in host)


def hyphen_count(host):
    return host.count("-")


def extract_features(host):
    return {
        "length": hostname_length(host),
        "digits": digit_count(host),
        "hyphens": hyphen_count(host),
        "has_brand": int(has_brand(host)),
        "is_official": int(is_official(host)),
    }

import re

# brand keyword -> its official domains
BRANDS = {
    "ais": ["ais.th", "ais.co.th"],
    "shopee": ["shopee.co.th", "shopee.com"],
    "lazada": ["lazada.co.th", "lazada.com"],
    "kerry": ["kerryexpress.com"],
    "paypal": ["paypal.com"],
    "apple": ["apple.com"],
    "netflix": ["netflix.com"],
}


def tokens(host):
    return re.split(r"[.-]", host)


def has_brand(host):
    return any(t.startswith(b) for t in tokens(host) for b in BRANDS)


def is_official(host):
    for domains in BRANDS.values():
        for d in domains:
            if host == d or host.endswith("." + d):
                return True
    return False