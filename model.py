from flask import Flask
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.impute import SimpleImputer
import joblib
from database_config import db, Transaction
from datetime import datetime, timedelta
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session management

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
db.init_app(app)

def generate_data_from_transactions():
    with app.app_context():
        transactions = Transaction.query.filter(Transaction.status != 'pending').all()
        data = []
        for transaction in transactions:
            created_time = transaction.created_at
            confirmed_time = transaction.status

            if confirmed_time and confirmed_time != 'confirmed':
                try:
                    confirmed_time = datetime.fromisoformat(confirmed_time)
                    approval_time = (confirmed_time - created_time).total_seconds() / 60  # Convert to minutes
                    data.append((transaction.transaction_type, transaction.amount, approval_time))
                except ValueError as e:
                    print(f"Erreur lors de l'analyse de confirmed_time pour la transaction {transaction.transaction_id}: {e}")

        if not data:
            print("Aucune donnée de transaction valide trouvée.")

        df = pd.DataFrame(data, columns=['type_transaction', 'montant', 'temps_approbation'])
        return df

def train_linear_regression_model():
    df = generate_data_from_transactions()

    if df.empty:
        print("Aucune donnée disponible pour l'entraînement.")
        return None, None, None  # Return None if no data

    # One-Hot Encode the 'transaction_type' column
    encoder = OneHotEncoder(sparse_output=False)
    transaction_type_encoded = encoder.fit_transform(df[['type_transaction']])
    transaction_type_encoded_df = pd.DataFrame(transaction_type_encoded, columns=encoder.get_feature_names_out(['type_transaction']))

    # Combine encoded features with numerical features
    X = pd.concat([transaction_type_encoded_df, df[['montant']]], axis=1)
    y = df['temps_approbation']

    # Impute missing values in the input data
    imputer = SimpleImputer(strategy='mean')
    X_imputed = imputer.fit_transform(X)
    X = pd.DataFrame(X_imputed, columns=X.columns)

    # Scale the input features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    X = pd.DataFrame(X_scaled, columns=X.columns)

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train the Linear Regression model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Save the encoder, imputer, scaler, and model to use during prediction
    joblib.dump(encoder, 'encoder.joblib')
    joblib.dump(imputer, 'imputer.joblib')
    joblib.dump(scaler, 'scaler.joblib')
    joblib.dump(model, 'model.joblib')  # Save the model itself

    # Evaluate the model
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred, squared=False)
    r2 = r2_score(y_test, y_pred)

    # Plot histograms
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(10, 5))
    axes[0].hist(y_test, bins=20, alpha=0.5, color='blue', label='Temps d\'approbation réel')
    axes[0].hist(y_pred, bins=20, alpha=0.5, color='green', label='Temps d\'approbation prédit')
    axes[0].set_title('Distribution du temps d\'approbation')
    axes[0].legend()

    # Plot scatter plot
    axes[1].scatter(y_test, y_pred, alpha=0.5)
    axes[1].plot([y.min(), y.max()], [y.min(), y.max()], 'r--', lw=2)
    axes[1].set_xlabel('Réel')
    axes[1].set_ylabel('Prédit')
    axes[1].set_title('Temps d\'approbation réel vs prédit')

    # Save plots to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plot_data = base64.b64encode(buf.read()).decode('utf8')

    # Close plot to release memory
    plt.close()

    # Return model metrics and plot data
    return mse, rmse, r2, plot_data

def predict_approval_time_for_transaction(transaction):
    encoder = joblib.load('encoder.joblib')
    imputer = joblib.load('imputer.joblib')
    scaler = joblib.load('scaler.joblib')
    model = joblib.load('model.joblib')

    data = [(transaction.transaction_type, transaction.amount)]
    df_pending = pd.DataFrame(data, columns=['type_transaction', 'montant'])

    # One-Hot Encode the 'transaction_type' column
    transaction_type_encoded = encoder.transform(df_pending[['type_transaction']])
    transaction_type_encoded_df = pd.DataFrame(transaction_type_encoded, columns=encoder.get_feature_names_out(['type_transaction']))

    # Combine encoded features with numerical features
    X_pending = pd.concat([transaction_type_encoded_df, df_pending[['montant']]], axis=1)

    # Impute missing values in the input data
    X_pending_imputed = imputer.transform(X_pending)
    X_pending = pd.DataFrame(X_pending_imputed, columns=X_pending.columns)

    # Scale the input features
    X_pending_scaled = scaler.transform(X_pending)
    X_pending = pd.DataFrame(X_pending_scaled, columns=X_pending.columns)

    # Predict the approval time
    predicted_approval_time = model.predict(X_pending)[0]

    # Calculate the estimated approval time from now
    current_time = datetime.utcnow()

    try:
        estimated_approval_time = current_time + timedelta(minutes=predicted_approval_time)
    except OverflowError as e:
        # Handle the case where the timedelta exceeds valid datetime range
        # Log the error and set a default or safe value
        print(f"OverflowError: {e}. Handling gracefully.")
        estimated_approval_time = current_time + timedelta(days=1)  # Example: Set to a day from now

    return estimated_approval_time

if __name__ == "__main__":
    with app.app_context():
        transaction = Transaction.query.filter_by(transaction_id='7932f907-9749-41d9-94b5-d06364955dde').first()
        if transaction:
            predicted_time = predict_approval_time_for_transaction(transaction)
            print(f"Temps d'approbation prédit: {predicted_time}")
        else:
            print("Transaction non trouvée.")
