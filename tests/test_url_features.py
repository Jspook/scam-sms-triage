import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from build_url_dataset import to_hostname
from url_features import brand_distance, extract_features, has_brand, is_official, levenshtein


def test_to_hostname_drops_scheme_and_path():
    assert to_hostname("https://infohadiah-shopee74.blogspot.com/?m=1") == "infohadiah-shopee74.blogspot.com"


def test_extract_features_on_scam_like_host():
    f = extract_features("info-resmi325.blogspot.com")
    assert f == {"length": 26, "digits": 3, "hyphens": 1,
                 "has_brand": 0, "is_official": 0, "brand_distance": 3}


def test_brand_and_official():
    assert has_brand("infohadiah-shopee74.blogspot.com")
    assert not has_brand("raisin.com")
    assert is_official("seller.shopee.co.th")
    assert not is_official("fake-shopee.co.th")


def test_levenshtein():
    assert levenshtein("shopee", "sh0pee") == 1
    assert levenshtein("lazada", "lazadda") == 1
    assert levenshtein("paypal", "paypa1") == 1
    assert levenshtein("ais", "raisin") == 3


def test_brand_distance_catches_typo():
    assert brand_distance("sh0pee-th.xyz") == 1