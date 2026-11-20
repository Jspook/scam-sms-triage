"""Compare the average of each URL feature for scam (1) vs legit (0)."""
import pandas as pd

from url_features import extract_features

df = pd.read_csv("data/processed/url_dataset.csv")
features = pd.DataFrame([extract_features(h) for h in df["hostname"]])
features["label"] = df["label"]

print(features.groupby("label").mean().round(2).T)