# libraries
import numpy as np
import pandas as pd
from datetime import datetime as dt

import re
import json
import string

import spacy
from textblob import TextBlob

import MySQLdb
from tweepy import OAuthHandler, API, Stream, StreamListener


# Enteries
boundarybox_value = [float(i) for i in input('Enter Boundary Box To Extract Tweets From: ').split(',')] # To convert the boundarybox numbers into a list of floats
new_table = input('Do you want to create new table? (y/n) ') # to create new table or use existing one
tb_name   = input('Enter table name: ') # database table name
db_name  = 'twitter_db' # Default database

# initiate spacy pipeline
nlp = spacy.load('en_core_web_sm')

# extract twitter and mysql access details from text files
tw_access_details = pd.read_csv('/Users/haithamalabadla/Data Science/BrainStation/Project/Final Project/twitter_accessdetails.txt')#../twitter_accessdetails.txt')
db_access_details = pd.read_csv('/Users/haithamalabadla/Data Science/BrainStation/Project/Final Project/db_accessdetails.txt')

db_type  = db_access_details.Database[0]
username = db_access_details.username[0]
password = db_access_details.password[0]
host = db_access_details.host[0]
port = db_access_details.port[0]

# MySQL Connection
db = MySQLdb.connect(host = "localhost", user = username, passwd = password, db = db_name)
c = db.cursor()

try:
    # if user decided to create new table in the database, the below script will run
    if new_table == 'y':
        c.execute('DROP TABLE IF EXISTS `{}`'.format(tb_name)) # drop the table if already exists
        query_carete_tb = 'CREATE TABLE {} ( collected_date DATETIME, original_tweet_text varchar(500), tweet_text varchar(500), length int, spaces int, uppers int, punctuations int, questionsmark int, explainations int, polarity float, subjectivity float, polarity_class varchar(20), subjectivity_class varchar(20) )'.format(tb_name) # create new table
        c.execute(query_carete_tb) # execute the sql create new table query 
except:
    print('Error creating table in {} database'.format(db_name))


# Consumer API keys
API_key        = tw_access_details.api_key.values[0]
API_secret_key = tw_access_details.api_secrectkey.values[0]

# Access token & access token secret
Access_token        = tw_access_details.api_accesstoken.values[0]
Access_token_secret = tw_access_details.api_secrecttoken.values[0]

# Initiate Twitter API
auth = OAuthHandler(API_key, API_secret_key)
auth.set_access_token(Access_token, Access_token_secret)
api = API(auth)
auth = OAuthHandler(API_key, API_secret_key)
auth.set_access_token(Access_token, Access_token_secret)

# Insights from tweet
def extract_text_details(x):
    length = len(x) # lenght if each tweet
    spaces = sum([1 for l in x if l.isspace()]) # how many spaces in each tweet
    uppers = sum([1 for l in x if l.isupper()]) # how many uppercases in each tweet
    punctuations  = sum([1 for l in x if l in string.punctuation]) # how many punctuations in each tweet
    questionsmark = x.count('?') # how many question marks in each tweet
    explainations = x.count('!') # how many explaination marks in each tweet
    return length, spaces, uppers, punctuations, questionsmark, explainations

# Take off special characters and URLs
def re_remove_url(x):
    x = re.sub(r'http\S+', '', x) # remove URLs
    x = ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)"," ",x).split()) # remove special characters and extra spaces
    return x

# Polarity class
def polarity_status(x):
    if x == 0:
        return 'Neutral'
    elif x > 0.00 and x < 0.50:
        return 'Positive'
    elif x >= 0.50:
        return 'Very Positive'
    elif x < 0.00 and x > -0.50:
        return 'Negative'
    elif x <= -0.50:
        return 'Very Negative'
    else:
        return 'Unknown'

# Subjectivity class
def subjectivity_status(x):
    if x == 0:
        return 'Very Objective'
    elif x > 0.00 and x < 0.40:
        return 'Objective'
    elif x >= 0.40 and x < 0.70:
        return 'Subjective'
    elif x >= 0.70:
        return 'Very Subjective'
    
# Polarity and Subjectivity percentages and status
def polarity_subjectivity(x):
    analysis = TextBlob(x)
    polarity = round(analysis.polarity, 2)
    subjectivity   = round(analysis.subjectivity, 2)
    polarity_class = polarity_status(polarity)
    subjectivity_class = subjectivity_status(subjectivity)
    return polarity, subjectivity, polarity_class, subjectivity_class

# extra stop words
stopwords_list = ['lol', 'lmao', 'tell', 'twitter', 'list', 'whatever', 'lmfaooooooooooooooooo', 'cuz', 'ass', 'fuck', 'lmfaoo', 'wtf', 
                  'sis', 'bro', 'jajajaajajajaja', 'jajaja', 'jaja', 'haha', 'shit', 'bro', 'sis', 'dad', 'mum', 'mam', 'yaa', 'yes', 
                  'lmfao', 'like', 'im', 'know', 'just', 'dont', 'thats', 'right', 'people', 'youre', 'got', 'gonna', 'time', 'think', 
                  'yeah', 'said', 'amp', 'omg', 'lmaoo', 'don', 'bio', 'lmaoooo', 'say', 'like', 'don', 'lmfaoooo', 'lmaooo', 'boy', 
                  'lot', 'doeee', 'sir', 'nt', 'girl']

def cleaning_tweets(x):
    # Spacy pipeline
    tweet = nlp(x)
    # Extract lemmatized words in lower case format if not digits, not punctuation, not stopword, and lenght not less than 2 
    tweet = ' '.join([token.lemma_.lower() for token in tweet if not token.is_stop and not token.is_punct and not token.text.isdigit() and len(token.text) > 2])
    tweet = ' '.join([token for token in tweet.split() if token not in stopwords_list])
    return tweet

# # **Streaming Class**
class listener(StreamListener):

    def on_data(self, data):

        # data object is Json
        all_data = json.loads(data)
        
        # Tweet's details
        collected_date        = dt.now()
        tweet_text            = all_data['text']
        is_verified           = all_data['user']['verified']
        num_followers         = all_data['user']['followers_count']
        num_friends           = all_data['user']['friends_count']

        # Coordination stores as [longitude, latitude] I ight need to flip them for later use
        if all_data['coordinates'] != None:
            coordinates = all_data['coordinates']['coordinates']
            longitude   = all_data['coordinates']['coordinates'][0]
            latitude    = all_data['coordinates']['coordinates'][1]
        else:
            coordinates = 'None'
            longitude   = 'None'
            latitude    = 'None'
        #print((tweet_text, is_verified, num_followers, num_friends, coordinates),'\n')

        # Inisghts and cleaning for username, screenname, tweet_text
        length, spaces, uppers, punctuations, questionsmark, explainations = extract_text_details(tweet_text)   # length, spaces, uppers, punctuations, questionsmark, explainations
        #print('Insights collected')
        
        # Keep orginal tweet
        original_tweet_text = tweet_text.encode()
        #print('Original tweet kept')
        
        # Remove URLs
        tweet_text = re_remove_url(tweet_text)                                                                  # x
        #print('URL removed')           
        
        if len(tweet_text) != 0:
            
            polarity, subjectivity, polarity_class, subjectivity_class = polarity_subjectivity(tweet_text)          # polarity, subjectivity, polarity_class, subjectivity_class
            #print('polarity, subjectivity, polarity_class, subjectivity_class are collected')
            
            tweet_text = cleaning_tweets(tweet_text)                                                                # tweet
            #print('Tweet text cleaned')
            
            c.execute('INSERT INTO {} (collected_date, original_tweet_text, tweet_text, length, spaces, uppers, punctuations, questionsmark, explainations, polarity, subjectivity, polarity_class, subjectivity_class) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'.format(tb_name), (collected_date, original_tweet_text, tweet_text, length, spaces, uppers, punctuations, questionsmark, explainations, polarity, subjectivity, polarity_class, subjectivity_class))
            #print('SQL query - insert - executed')
            
            db.commit()
            #print('Transaction committed')
            #print(tweet_text, length, spaces, uppers, punctuations, questionsmark, explainations, polarity, subjectivity, polarity_class, subjectivity_class)

        return True

    def on_error(self, status):
        print(status)

# function to start streaming with specific bounding box and language
def start_streaming(boundarybox):
    twitterStream = Stream(auth, listener())
    twitterStream.filter(locations = boundarybox, languages = ['en'])


boundarybox = boundarybox_value 

# Call the strat streaming function to start fetching the tweets
start_streaming(boundarybox)

