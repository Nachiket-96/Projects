from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

app = Flask(__name__)
CORS(app)

# Load the dataset
try:
    historical_data = pd.read_csv('canadian_immegration_data.csv')  # Replace with your historical data file
except FileNotFoundError:
    raise Exception("Error: 'canadian_immigration_data.csv' not found!")

# Extract unique countries
countries = historical_data['Country'].unique().tolist()
years = list(map(str, range(1990, 2024)))  # Historical years

@app.route('/')
def home():
    return "Welcome to the Immigration Data Visualization API!"

@app.route('/initialize', methods=['GET'])
def initialize():
    """
    Provide country and year options for the frontend dropdowns.
    """
    future_years = list(map(str, range(2024, 2029)))
    return jsonify({'countries': countries, 'years': years + future_years})

@app.route('/get_data', methods=['POST'])
def get_data():
    """
    Fetch immigration data for selected countries and years, including predictions.
    """
    request_data = request.get_json()
    selected_countries = request_data.get('countries')
    selected_years = request_data.get('years')

    # Prepare filtered data and predictions
    filtered_data = []
    chart_labels = selected_years
    chart_datasets = []

    for country in selected_countries:
        country_data = historical_data[historical_data['Country'] == country]
        X = np.array(list(map(int, years))).reshape(-1, 1)  # Years as feature
        y = country_data[years].values.flatten()  # Immigration numbers as target

        # Train model on historical data
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X, y)

        # Predict future values
        future_years = np.array(range(2024, 2029)).reshape(-1, 1)
        future_predictions = rf_model.predict(future_years)

        # Combine historical and future data
        combined_years = list(map(int, years)) + list(range(2024, 2029))
        combined_values = list(y) + list(future_predictions)

        # Add data to filtered_data and chart_datasets
        for year, value in zip(combined_years, combined_values):
            if str(year) in selected_years:
                filtered_data.append({'country': country, 'year': str(year), 'immigration': int(value)})

        # Add chart data
        chart_datasets.append({
            'label': country,
            'data': [int(value) for year, value in zip(combined_years, combined_values) if str(year) in selected_years],
            'backgroundColor': f'rgba({np.random.randint(0,255)}, {np.random.randint(0,255)}, {np.random.randint(0,255)}, 0.6)',
            'borderColor': f'rgba({np.random.randint(0,255)}, {np.random.randint(0,255)}, {np.random.randint(0,255)}, 1)',
            'borderWidth': 1
        })

    return jsonify({'data': filtered_data, 'chart': {'labels': chart_labels, 'datasets': chart_datasets}})

if __name__ == '__main__':
    app.run(debug=True)
