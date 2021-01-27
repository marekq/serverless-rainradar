from aws_lambda_powertools import Logger, Tracer
from datetime import datetime, timedelta

import json, requests, os, pytz
import matplotlib.pyplot as plt

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
    msg = 'no rain'

    # set output message and rainchance to blank
    timest = []
    intensity = []

    # get lat and lon
    lat, lon = os.environ['latlon'].split(',')
    
    url = "https://data.climacell.co/v4/timelines"

    # set time now and time plus three hours for forecase
    start = datetime.now()
    starttime = start.strftime('%Y-%m-%dT%H:%M:%SZ')

    end = datetime.now() + timedelta(hours = 2)
    endtime = end.strftime('%Y-%m-%dT%H:%M:%SZ')

    # create query string for api
    querystring = {
        "location": os.environ['latlon'],
        "fields": "precipitationIntensity",
        "timesteps": "5m",
        "units": "metric",
        "startTime": starttime,
        "endTime": endtime,
        "apikey": os.environ['apikeyclimacell']
    }

    # request the forecase from climacell api
    resp = requests.request("GET", url, params = querystring)
    response = json.loads(resp.text)
    print(response)

    # go over interval responses
    for item in response['data']['timelines'][0]['intervals']:
    
        # get time in Central European Timezone
        utc_now = pytz.utc.localize(datetime.strptime(item['startTime'], '%Y-%m-%dT%H:%M:%SZ'))
        cet_now = utc_now.astimezone(pytz.timezone("Europe/Amsterdam"))

        # get precipation value
        precipation = int(item['values']['precipitationIntensity'])

        # add precipation and timestamp to lists
        intensity.append(precipation)

        # create valid, human readable timestamp (such as 11:34)
        timest.append(str(cet_now.hour).zfill(2) + ":" + str(cet_now.minute).zfill(2))
        
        # if rain is expected, set sendmessage to true
        if precipation > 0:
            sendmsg = True
            msg = 'rain expected'

    # if rain detected, send message
    if sendmsg:
        print('rain forecasted, sending message')

        # generate line graph
        gen_graph(timest, intensity)

        # send the message to mobile devices
        send_message(msg, "rain forcasted")

    else:
        print('no rain forecasted, quitting')

# generate line graph for push message
@tracer.capture_method(capture_response = False)
def gen_graph(timest, intensity):

    plt.plot(timest, intensity)
    plt.xticks(rotation = 'vertical')
    plt.savefig('/tmp/plot.png')

# main handler
@tracer.capture_lambda_handler
def lambda_handler(event, context):

    get_weather()
