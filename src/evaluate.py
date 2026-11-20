"""Split the URL dataset, then evaluate the rule baseline on the test part."""
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.model_selection import train_test_split

from url_features import has_brand, is_official

SEED = 42


def baseline_predict(host):
    """Rule: brand keyword present AND not an official domain -> scam (1)."""
    return int(has_brand(host) and not is_official(host))


def report(name, y_true, y_pred):
    print(f"== {name} ==")
    print("precision:", round(precision_score(y_true, y_pred, zero_division=0), 3))
    print("recall:   ", round(recall_score(y_true, y_pred), 3))
    print("confusion matrix [[TN FP] [FN TP]]:")
    print(confusion_matrix(y_true, y_pred))


def main():
    df = pd.read_csv("data/processed/url_dataset.csv")
    train, test = train_test_split(
        df, test_size=0.25, stratify=df["label"], random_state=SEED
    )
    print(f"train={len(train)} test={len(test)} scam_in_test={test['label'].sum()}")
    y_pred = [baseline_predict(h) for h in test["hostname"]]
    report("baseline (rule)", test["label"], y_pred)


if __name__ == "__main__":
    main()