import joblib

model, threshold = joblib.load("data/final_model.joblib")

def predict_with_model(df):
    prob = model.predict_proba(df)[:, 1][0]
    return {
        "probability": round(prob, 4),
        "is_ad": prob > threshold
    }