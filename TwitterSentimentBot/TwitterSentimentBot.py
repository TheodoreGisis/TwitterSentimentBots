
import config
import requests
import os
import json
import csv
from csv import writer
from ernie import SentenceClassifier 
from BinanceFuturesPy.futurespy import Client as TestnetClient
from BinanceFuturesPy.futurespy import MarketData 
from binance.client import Client as ClientReal
from binance.enums import *
import numpy as np

import requests
from bs4 import BeautifulSoup



#Usefull library that cleans the tweets that we receive
import preprocessor

#Usefull librart to detect the language of the tweet
from langdetect import detect

#For the Binance_testnet enviroment
CHECK_IF_WE_TRADE_IN_TESTNET = True

TRADE_SYMBOL ="BTCUSDT"
TRADE_QUANTITY = 0.02


client = TestnetClient(config.Testnet_Binance_Api_key,config.Testnet_Binance_Secret_key,testnet=CHECK_IF_WE_TRADE_IN_TESTNET)
RealClient =  ClientReal(config.Binance_Api_Key,config.Binance_secret_key)
class TwitterSentimentBot:
    #for more details about these functions bearer_oauth(r),get_rules(),delete_all_rules(rules),set_rules(delete),get_stream(set) just read the twitter doc.

    def __init__(self):
        self.classifier = SentenceClassifier(model_path='./output' )
    #take the bearer token key from our config.py file
        self.bearer_token =config.TWITTER_BEARER_TOKEN
    #With self.position we secure to disaple an infinity loop when we place an order
        self.position = False

        self.sentimendList= []


    def get_cnn_index(self):

        CNNlink = requests.get("https://money.cnn.com/data/fear-and-greed/")
        soup = BeautifulSoup(CNNlink.content , 'html.parser')
        find = soup.find (id="needleChart")
        data = find.findAll("li")
        mydata = str(data[0])
        res = [int(i) for i in mydata.split() if i.isdigit()]
        return int(res[0])



    def bearer_oauth(self,r):
        """
        Method required by bearer token authentication.
        """
        r.headers["Authorization"] = f"Bearer {self.bearer_token}"
        r.headers["User-Agent"] = "v2FilteredStreamPython"
        return r

    def Average(self,list):
        if len(list) == 0:
            return len(list)
        else:
            return sum(list[-self.needofsentiments: ]) / self.needofsentiments
 
    def create_an_order(self,side,symbol,quantity):
        global CHECK_IF_WE_TRADE_IN_TESTNET
        try:
            print("SENDING ORDER.......")
            if CHECK_IF_WE_TRADE_IN_TESTNET:
                order = client.new_order(symbol=symbol , side= side, orderType="MARKET",quantity=quantity)
            else:
                order = RealClient.create_order(symbol=symbol, side=side, orderType= 'MARKET' , quantity = quantity)
            print(order)
        except Exception as e:
                print("ERROR MAKING THE ORDER......")
                print(e)
                return False
        return True

    def get_rules(self):
        response = requests.get(
            "https://api.twitter.com/2/tweets/search/stream/rules", auth=self.bearer_oauth
        )
        if response.status_code != 200:
            raise Exception(
                "Cannot get rules (HTTP {}): {}".format(response.status_code, response.text)
            )
        print(json.dumps(response.json()))
        return response.json()


    def delete_all_rules(self,rules):
        if rules is None or "data" not in rules:
            return None

        ids = list(map(lambda rule: rule["id"], rules["data"]))
        payload = {"delete": {"ids": ids}}
        response = requests.post(
            "https://api.twitter.com/2/tweets/search/stream/rules",
            auth=self.bearer_oauth,
            json=payload
        )
        if response.status_code != 200:
            raise Exception(
                "Cannot delete rules (HTTP {}): {}".format(
                    response.status_code, response.text
                )
            )
        print(json.dumps(response.json()))


    def set_rules(self,delete):
        sample_rules = [
            {"value": "BITCOIN", "tag": "BITCOIN"},
        ]
        payload = {"add": sample_rules}
        response = requests.post(
            "https://api.twitter.com/2/tweets/search/stream/rules",
            auth=self.bearer_oauth,
            json=payload,
        )
        if response.status_code != 201:
            raise Exception(
                "Cannot add rules (HTTP {}): {}".format(response.status_code, response.text)
            )
        print(json.dumps(response.json()))


    def get_stream(self,set):
        response = requests.get(
            "https://api.twitter.com/2/tweets/search/stream", auth=self.bearer_oauth, stream=True,
        )
        print(response.status_code)
        if response.status_code != 200:
            raise Exception(
                "Cannot get stream (HTTP {}): {}".format(
                    response.status_code, response.text
                )
            )
        for response_line in response.iter_lines():
            if response_line:
                json_response = json.loads(response_line)
                #Here we take the tweet and with the preprocessor library we clean it.
                tweet= json_response['data']['text']
                tweet = preprocessor.clean(tweet)
                tweet = tweet.replace(":","")
                try:
                #Here we only take the English tweets
                    if detect(tweet)=='en':
                        print(tweet)
                        try:
                            #-1 --> Bearish
                            #0 --> Neutral
                            #1 -->Bullish
                            classes= ["Bearish" ,"Neutral", "Bullish"]
                            probabilities = self.classifier.predict_one(tweet)
                            polarity =classes[np.argmax(probabilities)]
                            print(polarity)
                            self.sentimendList.append(polarity)
                            live_CNN_index = self.get_cnn_index()
                            print(live_CNN_index)

                            if len(self.sentimendList) > 20:
                                endlist = self.sentimendList[-20:]
                                print("--------------TOTAL BULISH:" + str(endlist.count('Bullish')))
                                print("--------------TOTAL Bearish:" + str(endlist.count('Bearish')))

                                if endlist.count('Bullish') > 6 and live_CNN_index < 40 :
                                    #BUY
                                    if self.position:
                                        print("--------------BUY...BUT WE OWN")
                                    else:
                                        print("--------------IT'S TIME TO BUY")
                                        #order= self.create_an_order(symbol=TRADE_SYMBOL,side="BUY",quantity=TRADE_QUANTITY)
                                        if order:
                                            self.position = True
                                elif endlist.count('Bearish') >6 and live_CNN_index >50:
                                    if self.position:
                                        print("--------------TIME TO SELL")
                                        #order= self.create_an_order(symbol=TRADE_SYMBOL,side="SELL",quantity=TRADE_QUANTITY)
                                        if order:
                                            self.position = False
                                    else:
                                        ("--------------SELL BUT WE OWN")
                        except:
                            pass
                        #mylist=[tweet]
                        #Creating the dataset for the machine learning
                        #with open(r'dataset.csv', 'a+',newline='') as f:
                         #   csv_writer= writer(f)
                          #  csv_writer.writerow(mylist)
                except:
                    pass
    def main(self):
        rules = self.get_rules()
        delete = self.delete_all_rules(rules)
        set = self.set_rules(delete)
        self.get_stream(set)


if __name__ == "__main__":
    TwittBot = TwitterSentimentBot()
    TwittBot.main()
