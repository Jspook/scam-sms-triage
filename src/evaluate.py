"""Split the URL dataset, then evaluate the rule baseline and the TF-IDF model on the test part."""
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from url_features import has_brand, is_official

SEED = 42


def baseline_predict(host):
    """Rule: brand keyword present AND not an official domain -> scam (1)."""
    return int(has_brand(host) and not is_official(host))


def make_model():
    """TF-IDF (char 3-5) + Logistic Regression. Phase 3 (src/triage.py) reuses this same setup."""
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)),
        LogisticRegression(max_iter=1000, class_weight="balanced"),
    )


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
    model = make_model()
    model.fit(train["hostname"], train["label"])   # learn from train only
    report("TF-IDF + LogReg", test["label"], model.predict(test["hostname"]))
    
    test = test.assign(pred=model.predict(test["hostname"]))
    print("\nFalse positives (legit flagged as scam):")
    print(test[(test.label == 0) & (test.pred == 1)]["hostname"].to_string())
    print("\nFalse negatives (scam we missed):")
    print(test[(test.label == 1) & (test.pred == 0)]["hostname"].to_string())


if __name__ == "__main__":
    main()