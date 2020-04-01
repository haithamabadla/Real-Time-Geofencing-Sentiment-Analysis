# import libraries
import dash
from dash.dependencies import Output, Input, State
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html

import plotly.graph_objs as go

import MySQLdb
import numpy as np
import pandas as pd
from wordcloud import WordCloud
from datetime import datetime as dt

# import access details
db_access_details = pd.read_csv('/Users/haithamalabadla/Data Science/BrainStation/Project/Final Project/db_accessdetails.txt')

# extract access details into objects
db_type  = db_access_details.Database[0]
username = db_access_details.username[0]
password = db_access_details.password[0]
host = db_access_details.host[0]
port = db_access_details.port[0]

# table name (for real-time, ensure that you update the table name according to 'stream.py' app)
tb_name  = 'twitter_tb_100'

# initiate dash application
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


# overview summary
description = 'Twitter is an online news and social networking site where people communicate in short messages called tweets. \
                Recently, it has been used increasingly by governments and politicians. The aim of this project is to analyse \
                tweets made by Obama and Trump to determine any similarities or differences in their personalities, professionalism \
                and keywords used.'

# creating blocks
# sentiment analysis line chart block that updated every second
sentiment_analysis_block = dcc.Graph(id="sentiment_graph", animate = True), dcc.Interval(id = 'sentiment-update', interval = 1 * 1000)
# polarity bar chart block that updated every 5 second
polarity_block = dcc.Graph(id = 'polarityClasses-graph', animate = True), dcc.Interval(id = 'polarityClasses-update', interval = 5 * 1000)
# wordcloud block that updated every 10 second
wc_block = dcc.Graph(id = 'wc-graph', animate = True), dcc.Interval(id = 'wc-update', interval = 10 * 1000)

wc_header = html.Div([html.H1("Find out what they are chatting about RIGHT NOW in Ontario!"),
            html.P("These are the most common words that twitter's users are using right now!")],
            style = {'padding': '80px', 'backgroundColor': '#00acee', 'color': '#FFFFFF'})

app.layout = html.Div(
    [
    	# adding a header and a paragraph
		html.Div([
			html.H1("Sentiment Analysis"),
			html.P(description)], 
			style = {'padding' : '70px' , 
			'backgroundColor' : '#00acee',
			'color': '#FFFFFF'}),
        # adding row with 2 columns that contain line and bar charts for sentiment analysis
        dbc.Row(
        	[
                dbc.Col(sentiment_analysis_block),
                dbc.Col(polarity_block),
            ],
        ),
        # create row for the second header 
        dbc.Row(
            [
                dbc.Col(wc_header),
            ],
        ),
        # create row for the wordcloud
        dbc.Row(
            [
                dbc.Col(wc_block),
            ],
        ),
    ]
)


# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
# Scatter plot + Smooth line sentiment analysis (mean)
@app.callback(Output('sentiment_graph', 'figure'), [Input('sentiment-update', 'n_intervals')])

def update_graph_scatter(input_data):

    # initiate the database connection
    db = MySQLdb.connect(host = "localhost", user = username, passwd = password, db = 'twitter_db', charset = 'utf8')
    # extract information from database table 
    df = pd.read_sql('select collected_date, polarity from {}'.format(tb_name), index_col = 'collected_date', con = db)
    # take the rolling mean for the polarity percentages to have a smooth line
    df['rolling_mean'] = df.polarity.rolling(int(len(df)/5)).mean()
    df.dropna(inplace = True) # drop null values (the first 5 rows when we do the rolling mean)

    # create the plotly figure
    X = df.index # datetime
    Y = df.rolling_mean # polarity rolling mean

    fig = {
        'data': [ go.Scatter( x=X, y=Y, mode='lines+markers', marker = dict(size = 3, color='LightSkyBlue', opacity=0.8))],
        'layout': go.Layout(title='', xaxis = dict(title = '', titlefont = dict(size = 8), tickfont = dict(size = 8)), yaxis = dict(title = 'Average Polarity', titlefont = dict(size = 8), tickfont = dict(size = 8)), hovermode='closest')#, height=450, width=850)
    }
    return fig
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
# Bar chart polarity classes
@app.callback(Output('polarityClasses-graph', 'figure'), [Input('polarityClasses-update', 'n_intervals')])

def update_graph_bar(input_data):
    # initiate the database connection
    db = MySQLdb.connect(host = "localhost", user = username, passwd = password, db = 'twitter_db', charset = 'utf8')
    # extract information from database table 
    polarity = pd.read_sql("select polarity_class from {} where polarity_class != 'Neutral'".format(tb_name), db)

    polarity_classes_list = ['Very Positive', 'Positive', 'Negative', 'Very Negative']

    # create plotly figure
    trace0  = go.Bar(y = ['Very Positive'], x = [polarity.polarity_class.value_counts()['Very Positive']], marker_color='#83CE91', name = 'Very Positive', orientation = 'h')
    trace1  = go.Bar(y = ['Positive'], x = [polarity.polarity_class.value_counts()['Positive']], marker_color='#BBE7C3', name = 'Positive', orientation = 'h')
    trace2  = go.Bar(y = ['Negative'], x = [polarity.polarity_class.value_counts()['Negative']], marker_color='#EA9999', name = 'Negative', orientation = 'h')
    trace3  = go.Bar(y = ['Very Negative'], x = [polarity.polarity_class.value_counts()['Very Negative']], marker_color='#CE4848', name = 'Very Negative', orientation = 'h')

    data   = [trace0, trace1, trace2, trace3] # Title = Polarity 5 minutes Rolling Average
    layout = go.Layout(title = '', xaxis = dict(title = '', titlefont = dict(size = 8), tickfont = dict(size = 8)), yaxis = dict(title = '', titlefont = dict(size = 8), tickfont = dict(size = 8), showticklabels=False), plot_bgcolor='#FFFFFF') #, width = 500)

    fig = go.Figure(data = data, layout = layout)

    return fig
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
# Wordcloud plot
@app.callback(Output('wc-graph', 'figure'), [Input('wc-update', 'n_intervals')])

def update_graph_wc(input_data):

    # import tweets and convert them into corpus
    db = MySQLdb.connect(host = "localhost", user = username, passwd = password, db = 'twitter_db', charset = 'utf8')
    df = pd.read_sql("select tweet_text from {}".format(tb_name), db)
    words = ' '.join(df.tweet_text) # convert all tweets into one document

    # initiate wc object and pass words into it
    wc = WordCloud(background_color = "white", colormap = "tab20c", max_font_size = 200, random_state = 42)
    wc.generate(words)

    # lists to collect extracted values
    word_list=[]
    freq_list=[]
    fontsize_list=[]
    position_list=[]
    orientation_list=[]
    color_list=[]

    # extract values 
    # 'wc' object contains all the information needed to extract what wee need and in this case,
    # in matplotlib it automatically display the words with their specific location, color and size, in plotly case, 
    # we have to manually extract these information from the layout_ method which contains 5 results, tuple and 4 other outputs.  
    for (word, freq), fontsize, position, orientation, color in wc.layout_:
        word_list.append(word)
        freq_list.append(freq)
        fontsize_list.append(fontsize)
        position_list.append(position)
        orientation_list.append(orientation)
        color_list.append(color)
        
    # store positions
    x=[]
    y=[]

    # get positions
    for i in position_list:
        x.append(i[0])
        y.append(i[1])
        
    # get the relative occurence frequencies
    new_freq_list = []

    for i in freq_list:
        new_freq_list.append(i*100)

    # generate plot
    trace = go.Scatter(x = x, y = y, textfont = dict(size = new_freq_list, color = color_list), hoverinfo = 'text', hovertext = ['{0}{1}'.format(w, f) for w, f in zip(word_list, freq_list)], mode = 'text', text = word_list)
    layout = go.Layout({'xaxis': {'showgrid': False, 'showticklabels': False, 'zeroline': False}, 'yaxis': {'showgrid': False, 'showticklabels': False, 'zeroline': False}, 'plot_bgcolor':'#FFFFFF'})

    fig = go.Figure(data = [trace], layout = layout)

    return fig
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////



if __name__ == '__main__':
    app.run_server(debug = True)

