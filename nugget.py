import requests, hashlib, json, time, ovh
from datetime import datetime
from random import randint

with open('config.json') as f:
    config = json.load(f)

# Instantiate. Visit https://api.ovh.com/createToken/?GET=/me
# to get your credentials
client = ovh.Client(
    endpoint=config['endpoint'],
    application_key=config['application_key'],
    application_secret=config['application_secret'],
    consumer_key=config['consumer_key'],
)

# Print nice welcome message
print("Welcome", client.get('/me')['firstname'])
availableDataCenter = "bhs"
retry = 0

def datacenterToRegion(availableDataCenter):
    if availableDataCenter == "bhs": 
        return "canada"
    else:
        return "europe"

def call(url,payload=None,runs=10):
    for run in range(runs):
        try:
            if payload:
                response = requests.post(url, headers=headers, data=json.dumps(payload))
            else:
                response = requests.get(url, headers=headers)
            if response.status_code == 200: return response
            print(f"Got {response.status_code} for {url} retrying...")
            print(json.dumps(response.json(), indent=4))
        except:
            pass
        time.sleep(5)
    exit(f"Unable to fetch {url}")

while True:
    headers = {'Accept': 'application/json','X-Ovh-Application':config['application_key'],'X-Ovh-Consumer':config['consumer_key'],
    'Content-Type':'application/json;charset=utf-8','Host':config['endpointAPI']}
    print("Preparing Package")
    #getting current time
    print("Getting Time")
    response = call(f"https://{config['endpointAPI']}/1.0/auth/time")
    timeDelta = int(response.text) - int(time.time())
    # creating a new cart
    cart = client.post("/order/cart", ovhSubsidiary=config['ovhSubsidiary'], _need_auth=False)
    #assign new cart to current user
    client.post("/order/cart/{0}/assign".format(cart.get("cartId")))
    #putting KS-A into cart
    #result = client.post(f'/order/cart/{cart.get("cartId")}/eco',{"duration":"P1M","planCode":"22sk010","pricingMode":"default","quantity":1})
    #apparently this shit sends malformed json whatever baguette
    payload = {'duration':'P1M','planCode':'24ska01','pricingMode':'default','quantity':1}
    call(f"https://{config['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/eco", payload)
    #getting current cart
    response = call(f"https://{config['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}")
    #modify item for checkout
    itemID = response.json()['items'][0]
    print(f'Getting current cart {cart.get("cartId")}')
    #set configurations
    configurations = [{'label':'region','value':config['region']},{'label':'dedicated_datacenter','value':config['dedicated_datacenter']},{'label':'dedicated_os','value':'none_64.en'}]
    for entry in configurations:
        print(f"Setting {entry}")
        call(f"https://{config['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/item/{itemID}/configuration",entry)
    #set options
    options = [{'itemId':itemID,'duration':'P1M','planCode':'bandwidth-100-24sk','pricingMode':'default','quantity':1},
            {'itemId':itemID,'duration':'P1M','planCode':'softraid-1x480ssd-24ska01','pricingMode':'default','quantity':1},
            {'itemId':itemID,'duration':'P1M','planCode':'ram-64g-noecc-2133-24ska01','pricingMode':'default','quantity':1}
    ]
    for option in options:
        print(f"Setting {option}")
        call(f"https://{config['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/eco/options", option)
    print("Package ready, waiting for stock")
    #the order expires after about 1 day
    for check in range(80000):
        now = datetime.now()
        print(f'Run {check+1} {now.strftime("%H:%M:%S")}')
        #wait for stock
        try:
            response = requests.get('https://us.ovh.com/engine/apiv6/dedicated/server/datacenter/availabilities?excludeDatacenters=false&planCode=24ska01&server=24ska01')
        except:
            time.sleep(2)
            continue
        if response.status_code == 200:
            stock = response.json()
            score = 0
            for datacenter in stock[0]['datacenters']:
                if datacenter['availability'] != "unavailable":
                    availableDataCenter = datacenter['datacenter'] 
                    score = score +1
        else:
            time.sleep(randint(5,10))
            continue
        #lets checkout boooyaaa
        if score >= 1:
            #autopay should be set to true if you want automatic delivery, otherwise it will just generate a invoice
            payload={'autoPayWithPreferredPaymentMethod':False,'waiveRetractationPeriod':False}
            #prepare sig
            target = f"https://{config['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/checkout"
            now = str(int(time.time()) + timeDelta)
            signature = hashlib.sha1()
            signature.update("+".join([config['application_secret'], config['consumer_key'],'POST', target, json.dumps(payload), now]).encode('utf-8'))
            headers['X-Ovh-Signature'] = "$1$" + signature.hexdigest()
            headers['X-Ovh-Timestamp'] = now
            response = requests.post(target, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                print(response.status_code)
                print(json.dumps(response.json(), indent=4))
                exit("Done")
            else:
                print("Got non 200 response code on checkout, retrying")
                retry += 1
                if retry > 10: exit()
                if retry == 5:
                    print(f"Switching Region to {datacenterToRegion(availableDataCenter)} and datacenter to {availableDataCenter}") 
                    config['dedicated_datacenter'] = availableDataCenter
                    config['region'] = datacenterToRegion(availableDataCenter)
                    break
            time.sleep(5)
        else:
            time.sleep(1)