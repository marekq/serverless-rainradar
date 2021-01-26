from aws_lambda_powertools import Logger, Tracer
import requests, os
import matplotlib.pyplot as plt

from buienradar.buienradar import (get_data, parse_data)
from buienradar.constants import (CONTENT, RAINCONTENT, SUCCESS)

modules_to_be_patched = ["boto3", "requests"]
tracer = Tracer(patch_modules = modules_to_be_patched)

logger = Logger()
tracer = Tracer()

@tracer.capture_method(capture_response = False)
def send_message(msg, rainchance):

    payload = {
        "token": os.environ['apiapptoken'],
        "user": os.environ['apiuserkey'],
        "message": msg,
        "title": str(rainchance) + " percent rain chance"
    }

    # send the message to pushover api
    p = requests.post("https://api.pushover.net/1/messages.json", data = payload, files = { "attachment" : ("plot.png", open("/tmp/plot.png", "rb"), "image/jpeg") } )

@tracer.capture_method(capture_response = False)
def get_weather():

    # set sendmsg to false
    sendmsg = False

    # set output message and rainchance to blank
    msg = ''
    rainchance = ''

    # get lat and lon
    lat, lon = os.environ['latlon'].split(',')
    
    # minutes to look ahead for precipitation forecast
    timeframe = 60

    # get results
    result = get_data(latitude = float(lat), longitude = float(lon))

    # if data was retrieved
    if result.get(SUCCESS):
        data = result[CONTENT]
        raindata = result[RAINCONTENT]

        result = parse_data(data, raindata, float(lat), float(lon), timeframe)
        
        rainchance = result['data']['forecast'][0]['rainchance']

        if rainchance > 0:
            sendmsg = True

            msg = result['data']['forecast'][0]['condition']['exact']

    # if rain detected, send message
    if sendmsg:
        print('rain forecasted, sending message')

        gen_graph(lat, lon)
        send_message(msg, rainchance)

    else:
        print('no rain forecasted, quitting')

def gen_graph(lat, lon):

    times = []
    rainmm = []

    url = "https://gpsgadget.buienradar.nl/data/raintext?lat=" + lat + "&lon=" + lon
    print(url)

    res = requests.request("GET", url)
    resp = str(res.text).split('|')

    for line in resp:
        if len(line) != 0:
            item = line.split('\r\n')

            if len(item) == int(2) and item[1] != '':
                times.append(item[0])

                if item[1] != '0':
                    rainmm.append(item[1].lstrip('0'))

                else:   
                    rainmm.append(item[1])

    plt.plot(times, rainmm)
    plt.xticks(rotation = 'vertical')
    plt.savefig('/tmp/plot.png')

# main handler
@tracer.capture_lambda_handler
def lambda_handler(event, context):

    get_weather()
