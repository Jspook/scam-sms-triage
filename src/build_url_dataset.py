"""Build a labeled hostname dataset: OpenPhish = scam (1), Tranco = legit (0)."""
import csv
import random
from pathlib import Path
from urllib.parse import urlparse

RAW = Path("data/raw")
OUT = Path("data/processed/url_dataset.csv")
N_LEGIT = 3000   # how many legit hostnames to sample
SEED = 42        # fixed seed so the sample is the same every run


def to_hostname(url):
    """Return the hostname of a URL, or None if it has none."""
    return urlparse(url.strip()).hostname


def load_phish():
    lines = (RAW / "openphish_feed.txt").read_text(encoding="utf-8").splitlines()
    hosts = {to_hostname(line) for line in lines if line.strip()}
    return {h for h in hosts if h}


def load_legit():
    with open(RAW / "tranco" / "top-1m.csv", encoding="utf-8") as f:
        domains = [row[1] for row in csv.reader(f) if int(row[0]) <= 100_000]
    random.seed(SEED)
    return set(random.sample(domains, N_LEGIT))


def main():
    phish = load_phish()
    legit = load_legit() - phish
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hostname", "label", "source"])
        for h in sorted(phish):
            w.writerow([h, 1, "openphish"])
        for h in sorted(legit):
            w.writerow([h, 0, "tranco"])
    print(f"phish={len(phish)} legit={len(legit)} -> {OUT}")


if __name__ == "__main__":
    main()