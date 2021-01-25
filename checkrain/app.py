from aws_lambda_powertools import Logger, Tracer
import matplotlib, requests, os
    
modules_to_be_patched = ["boto3", "requests"]
tracer = Tracer(patch_modules = modules_to_be_patched)

logger = Logger()
tracer = Tracer()

@tracer.capture_method(capture_response = False)
def send_message(out):


    img_url = "http://api.buienradar.nl/image/1.0/RadarMapNL?w=512&h=512"

    payload = {
        "token": os.environ['apiapptoken'],
        "user": os.environ['apiuserkey'],
        "message": 'Rain Alert',
        "url": img_url
    }

    # get the image url
    print('get image url ' + img_url)
    r = requests.get(img_url)

    # store the image url on /tmp
    filen = open('/tmp/map.gif', 'wb')
    filen.write(r.content)
    filen.close()

    # send the message to pushover api
    p = requests.post("https://api.pushover.net/1/messages.json", data = payload, files = { "attachment" : ("map.gif", open("/tmp/map.gif", "rb"), "image/jpeg") } )
    print(p.text)

@tracer.capture_method(capture_response = False)
def get_weather():

    # create out object
    out = ['']

    # set sendmsg to false - temp disabled for debugging
    sendmsg = True

    # get lat and lon
    lat, lon = os.environ['latlon'].split(',')
    url = "https://gpsgadget.buienradar.nl/data/raintext?lat=" + lat + "&lon=" + lon
    
    print('get rain info url')

    # retrieve rain info
    response = requests.request("GET", url)

    # split lines in output
    resp = str(response.text).split('|')
    
    # check all retrieved records
    for line in resp:

        if len(line) != 0:
            item = line.split('\r\n')
            out.append(( item[0], item[1] ))

            # if rain value is higher than 0, append and send message
            if len(item) == int(2) and item[1] != '' and item[1] != '000':
                sendmsg = True

    # if rain detected, send message
    if sendmsg:
        print('rain forecasted, sending message')
        send_message(out)

    else:
        print('no rain forecasted, quitting')

# main handler
@tracer.capture_lambda_handler
def lambda_handler(event, context):

    get_weather()
