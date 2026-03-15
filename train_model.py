import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error

from xgboost import XGBRegressor


data = pd.read_csv("auction_dataset.csv")

encoder = LabelEncoder()

data["category"] = encoder.fit_transform(data["category"])

X = data[[
    "starting_price",
    "market_avg",
    "seller_rating",
    "bid_count",
    "duration",
    "category",
    "popularity",
    "condition_score"
]]

y = data["final_price"]


X_train,X_test,y_train,y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


model = XGBRegressor(

    n_estimators=600,
    learning_rate=0.03,
    max_depth=6,
    subsample=0.9,
    colsample_bytree=0.9,
    random_state=42
)


model.fit(X_train,y_train)


pred = model.predict(X_test)

print("Mean Absolute Error:",mean_absolute_error(y_test,pred))


joblib.dump(model,"model/price_model.pkl")

joblib.dump(encoder,"model/category_encoder.pkl")

print("Model saved successfully")