import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score

# --- Load
df = pd.read_csv('subset_100motobikes.csv')

# --- Cleaning helpers
def to_number(s):
    if pd.isna(s): return np.nan
    s = str(s)
    s = s.replace('₫','').replace('VND','').replace('vnd','')
    s = s.replace(',','').replace('.','').replace(' ','')
    s = ''.join(ch for ch in s if ch.isdigit() or ch=='-')
    return float(s) if s not in ['', '-'] else np.nan

# Convert target
df['price'] = df['Giá'].apply(to_number)

# Example numeric features after cleaning
df['mileage'] = df['Số Km đã đi'].apply(lambda s: to_number(s))
df['year_reg'] = df['Năm đăng ký'].apply(lambda s: to_number(s))
# Age feature
CURRENT_YEAR = 2025
df['age'] = CURRENT_YEAR - df['year_reg']

# Example categorical features
cat_feats = ['Thương hiệu', 'Dòng xe', 'Tình trạng', 'Loại xe']
num_feats = ['mileage', 'age']

# Drop rows without price
df = df.dropna(subset=['price'])

X = df[num_feats + cat_feats]
y = df['price']

# Preprocessing
num_transformer = Pipeline(steps=[
    ('scaler', StandardScaler())
])

cat_transformer = Pipeline(steps=[
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

preprocessor = ColumnTransformer(transformers=[
    ('num', num_transformer, num_feats),
    ('cat', cat_transformer, cat_feats)
])

model = Pipeline(steps=[
    ('preproc', preprocessor),
    ('reg', RandomForestRegressor(n_estimators=200, random_state=42))
])

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model.fit(X_train, y_train)
print("Train R2:", model.score(X_train, y_train))
print("Test R2:", model.score(X_test, y_test))

# Cross-val
from sklearn.model_selection import cross_val_score
scores = cross_val_score(model, X, y, cv=5, scoring='neg_root_mean_squared_error')
print("5-fold RMSE:", -scores.mean())

# Save model
import pickle
with open('motobike_price_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model saved to motobike_price_model.pkl")
