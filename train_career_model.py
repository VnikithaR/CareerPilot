
import os
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATASET_PATH = os.path.join(
    BASE_DIR, "career_training_data.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR, "career_model.joblib"
)


def train_model():
    print("Loading career training dataset...")

    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    data = pd.read_csv(DATASET_PATH)

    required_columns = {"skills", "career"}

    if not required_columns.issubset(data.columns):
        raise ValueError(
            "CSV must contain 'skills' and 'career' columns."
        )

    data = data.dropna(subset=["skills", "career"])
    data["skills"] = data["skills"].astype(str).str.strip()
    data["career"] = data["career"].astype(str).str.strip()
    data = data[
        (data["skills"] != "") &
        (data["career"] != "")
    ]

    if data["career"].nunique() < 2:
        raise ValueError(
            "The dataset must contain at least two career classes."
        )

    print(f"Total examples: {len(data)}")
    print(f"Career categories: {data['career'].nunique()}")

    # Split data for evaluation
    X_train, X_test, y_train, y_test = train_test_split(
        data["skills"],
        data["career"],
        test_size=0.25,
        random_state=42,
        stratify=data["career"]
    )

    # Build the ML pipeline
    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                sublinear_tf=True
            )
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                random_state=42
            )
        )
    ])

    print("Training career prediction model...")
    model.fit(X_train, y_train)

    # Evaluate using held-out examples
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    print("\nEvaluation results")
    print("------------------")
    print(f"Test accuracy: {accuracy:.2%}")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0
        )
    )

    # Retrain using all available examples
    print("Training final model on all dataset examples...")
    model.fit(data["skills"], data["career"])

    joblib.dump(model, MODEL_PATH)

    print(f"\nModel saved successfully: {MODEL_PATH}")
    print("Career model training completed.")


if __name__ == "__main__":
    train_model()