"""Turn a hostname into numeric features a model can use."""
import re

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
        "brand_distance": brand_distance(host),
    }


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

def levenshtein(a, b):
    """Minimum number of single-letter edits to turn a into b."""
    prev = list(range(len(b) + 1))           # turning "" into b[:j] costs j
    for i, ca in enumerate(a, start=1):
        cur = [i]                            # turning a[:i] into "" costs i
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(min(
                prev[j] + 1,                 # delete
                cur[j - 1] + 1,              # insert
                prev[j - 1] + cost,          # replace (or keep)
            ))
        prev = cur
    return prev[-1]


def brand_distance(host):
    """Smallest edit distance between any token and any brand keyword."""
    return min(levenshtein(t, b) for t in tokens(host) if t for b in BRANDS)