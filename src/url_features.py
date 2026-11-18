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
    }