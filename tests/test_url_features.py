import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from build_url_dataset import to_hostname
from url_features import extract_features


def test_to_hostname_drops_scheme_and_path():
    assert to_hostname("https://infohadiah-shopee74.blogspot.com/?m=1") == "infohadiah-shopee74.blogspot.com"


def test_extract_features_on_scam_like_host():
    f = extract_features("info-resmi325.blogspot.com")
    assert f == {"length": 26, "digits": 3, "hyphens": 1}