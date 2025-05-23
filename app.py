#import libraries
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
import datetime
from datetime import date, timedelta
from statsmodels.tsa.seasonal import seasonal_decompose
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

# Title
app_name = 'StockAI'
st.title(app_name)
st.subheader('This app is created to forecast the stock market price of the entered company.')  # Updated text

# Add an image from online resource
st.image('https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ4EBx9mg3Tzc8Xg4ayJi2wtrXGjJDNHBc8KQ&s')

# Take input from the user of app about the start and end date

# Sidebar
st.sidebar.header('Select the parameters from below')

start_date = st.sidebar.date_input('Start Date', date(2018, 1, 1))
#END DATE SELECT
tomorrow = date.today() - timedelta(days=1)
end_date = st.sidebar.date_input('End Date', tomorrow)

# Get ticker symbol from user input
ticker = st.sidebar.text_input('Enter the company ticker symbol (e.g., AAPL)').strip().upper()  # New text input

# Validate ticker input
if not ticker:
    st.sidebar.error("Please enter a ticker symbol.")
    st.stop()

# Fetch data from inputs using yfinance library
data = yf.download(ticker, start=start_date, end=end_date)

# Check if data is downloaded correctly
if data.empty:
    st.error(f"No data found for ticker symbol '{ticker}'. Please enter a valid symbol.")
    st.stop()

# Rest of your code remains the same...
# [No changes needed beyond this point except the removed ticker_list]
# Flatten MultiIndex columns if present
if isinstance(data.columns, pd.MultiIndex):
    data.columns = [' '.join(col).strip() for col in data.columns.values]

# Add Date as a column to the dataframe
data.insert(0, "Date", data.index)
data.reset_index(drop=True, inplace=True)
st.write('Data from', start_date, 'to', end_date)
st.write(data)

# Plot the data
st.header('Data Visualization')
st.subheader('Plot of the data')
st.write("**Note:** Select your date range on the sidebar, or zoom in on the plot and select your specific column")
# Exclude 'Date' from the columns to plot
plot_columns = [col for col in data.columns if col != 'Date']
fig = px.line(data, x='Date', y=plot_columns, title='Closing price of the stock',width=1000, height=600)
st.plotly_chart(fig)

# add a select box to select column from data
column = st.selectbox('Select the colomn to be used for forecasting', plot_columns)

# sub-setting the data
data = data[['Date', column]]
st.write("Selected Data")
st.write(data)

# ADF test check stationarity
st.header('Is data stationary?')
st.write(adfuller(data[column])[1] < 0.05)

# lets decompose the data
st.header('Decomposition of the data')
decomposition = seasonal_decompose(data[column], model='additive', period=12)
st.write(decomposition.plot())

# make same plot in plotly
st.write('## Plotting the decomposition in plotly')
st.plotly_chart(px.line(x=data["Date"], y=decomposition.trend, title='Trend', width=1200, height=400, labels={'x': 'Date', 'y': 'price'}).update_traces(line_color='Blue'))
st.plotly_chart(px.line(x=data["Date"], y=decomposition.seasonal, title='Seasonality', width=1200, height=400, labels={'x': 'Date', 'y': 'price'}).update_traces(line_color='green'))
st.plotly_chart(px.line(x=data["Date"], y=decomposition.resid, title='Residuals', width=1200, height=400, labels={'x': 'Date', 'y': 'price'}).update_traces(line_color='Red', line_dash='dot'))

# Let's run the model
#  user input for three parameters of the model and seasonal order
p = st.slider('select the value of p', 0, 5, 2)
d = st.slider('Select the value of d', 0, 5, 1)
q = st.slider('select the value of q', 0, 5, 2)
seasonal_order = st.number_input('Select the value of seasonal p', 0, 24 , 12)

# Create and fit the model
model = sm.tsa.statespace.SARIMAX(data[column],
                                order=(p, d, q),
                                seasonal_order=(p, d, q, seasonal_order))
model = model.fit()

# print model summary
st.header('Model Summary')
st.write(model.summary())
st.write('---')

# predict the future values (Forecasting)
st.write("<p style='color:green; font-size: 50px; font-weight: bold;'>Forecasting the data</p>", unsafe_allow_html=True)

forecast_period = st.number_input('## Enter forecast period in days', 1, 1000, 150)

# predict the future values
predictions = model.get_prediction(start=len(data), end=len(data)+forecast_period)
predictions = predictions.predicted_mean

# add index to the predictions
predictions.index = pd.date_range(start=end_date, periods=len(predictions), freq='D')
predictions = pd.DataFrame(predictions)
predictions.insert(0, 'Date', predictions.index, True)
predictions.reset_index(drop=True, inplace=True)
st.write('Predictions',predictions)
st.write('Actual Data', data)
st.write("---")

# let's plot the data
fig = go.Figure()
# add actual data to the plot
fig.add_trace(go.Scatter(x=data['Date'], y=data[column],mode='lines', name='Actual', line=dict(color='blue')))
# add predicted data to the plot
fig.add_trace(go.Scatter(x=predictions['Date'], y=predictions["predicted_mean"],mode='lines', name='Predicted', line=dict(color='red')))
# set the title and axis labels
fig.update_layout(title='Actual vs Predicted', xaxis_title='Date', yaxis_title='Price', width=1200, height=400)
# display the plot
st.plotly_chart(fig)

# Add buttons to show and hide separate plots

st.write(px.line(x=data["Date"], y=data[column], title='Actual', width=1200, height=400,
                 labels={'x': 'Date', 'y': 'price'}).update_traces(line_color='Blue'))

st.write(px.line(x=predictions["Date"], y=predictions["predicted_mean"], title='Predicted', width=1200, height=400,
                 labels={'x': 'Date', 'y': 'price'}).update_traces(line_color='green'))






# TO CHECK ACCURACY

# 1. Define accuracy check period
try:
    # Calculate cutoff date (make sure we have enough data)
    accuracy_check_date = end_date - timedelta(days=forecast_period)

    # Convert to pandas datetime for comparison
    accuracy_check_date = pd.to_datetime(accuracy_check_date)
    last_available_date = pd.to_datetime(data['Date'].iloc[-1])

    if accuracy_check_date >= last_available_date:
        st.warning("Not enough historical data for accuracy check")
    else:
        # 2. Split data into train and test
        train_data = data[data['Date'] <= accuracy_check_date]
        test_data = data[data['Date'] > accuracy_check_date]

        if not test_data.empty:
            # 3. Train model on historical data
            model_accuracy = sm.tsa.statespace.SARIMAX(
                train_data[column],
                order=(p, d, q),
                seasonal_order=(p, d, q, seasonal_order)
            ).fit(disp=0)

            # 4. Generate predictions for test period
            predictions = model_accuracy.get_forecast(steps=len(test_data))
            pred_mean = predictions.predicted_mean

            # Create proper date index for predictions
            pred_dates = pd.date_range(
                start=train_data['Date'].iloc[-1] + timedelta(days=1),
                periods=len(test_data)
            )
            pred_mean.index = pred_dates

            # 5. Compare with actual data
            comparison = pd.DataFrame({
                'Date': test_data['Date'],
                'Actual': test_data[column],
                'Predicted': pred_mean.values
            })

            # Calculate metrics
            mae = np.mean(np.abs(comparison['Actual'] - comparison['Predicted']))
            mape = np.mean(np.abs((comparison['Actual'] - comparison['Predicted']) / comparison['Actual'])) * 100

            # Show results
            st.subheader(f'Accuracy Check ({forecast_period} Days Forecast)')
            st.write("Lower the MAE & MAPE = Better the Accuracy")
            col1, col2 = st.columns(2)
            col1.metric("MAE(Mean Absolute Error)", f"{mae:.2f}")
            col2.metric("MAPE(Mean Absolute Percentage Error)", f"{mape:.2f}%")

            # Plot comparison
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=comparison['Date'], y=comparison['Actual'], name='Actual'))
            fig.add_trace(go.Scatter(x=comparison['Date'], y=comparison['Predicted'], name='Predicted'))
            fig.update_layout(title='Historical Accuracy Validation')
            st.plotly_chart(fig)

        else:
            st.warning("No test data available for accuracy check")

except Exception as e:
    st.error(f"Accuracy check failed: {str(e)}")







st.write("---")
st.markdown("<h1 style='color: green;'>Thank you for using this app, <br>share with your friends!😄</h2>", unsafe_allow_html=True)

st.write("---")
st.write("### About the author:")

st.write("<p style='color:blue; font-weight: bold ; font-size: 50px; '>Aryan Kanada</p>", unsafe_allow_html=True)



st.write("## Connect with me on social media")
# add links to my social media
# urls of the images
linkedin_url = "https://img.icons8.com/color/48/000000/linkedin.png"
github_url = "https://img.icons8.com/fluent/48/000000/github.png"

# redirect urls
linkedin_redirect_url = "https://www.linkedin.com/in/aryankanada"
github_redirect_url = "https://github.com/Aryan-Kanada"

# add links to the images
st.markdown(f'<a href="{github_redirect_url}"><img src="{github_url}" width="60" height="60"></a>'
            f'<a href="{linkedin_redirect_url}"><img src="{linkedin_url}" width="60" height="60"></a>', unsafe_allow_html=True)
