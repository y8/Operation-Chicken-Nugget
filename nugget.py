import requests, hashlib, json, time, ovh, sys, os
from datetime import datetime
from random import randint

with open('config.json') as f: config = json.load(f)
with open('endpoints.json') as f: endpoints = json.load(f)
path = os.path.dirname(os.path.realpath(__file__))

if not "autoPay" in config: exit("autoPay missing in config.")
if not "anyDatacenter" in config: exit("anyDatacenter missing in config.")

if len(sys.argv) == 1:
    planConfig = {}
    print("Please select the endpoint for the catalog")
    for index, option in enumerate(endpoints): print(index, option)
    selected = input("Endpoint: ")
    for index, option in enumerate(endpoints):
        if int(selected) == index: 
            selectedEndpoint = endpoints[option]
            selectedEndpoint['endpointAPI'] = option
            break
else:
    if os.path.isfile(f"{path}/plans/{sys.argv[1]}"):
        print(f"Loading {sys.argv[1]}")
        with open(f"{path}/plans/{sys.argv[1]}") as handle: planConfig = json.loads(handle.read())
        selectedEndpoint = endpoints[planConfig['endpoint']]
        selectedEndpoint['endpointAPI'] = planConfig['endpoint']
    else:
        exit(f"Unable to find file plans/{sys.argv[1]}")

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
        except Exception as e:
            print(f"Failed to fetch {url} got error '{e}' retrying...")
        time.sleep(5)
    exit(f"Unable to fetch {url}")

headers = {'Accept': 'application/json','X-Ovh-Application':config['application_key'],'X-Ovh-Consumer':config['consumer_key'],
'Content-Type':'application/json;charset=utf-8','Host':selectedEndpoint['endpointAPI']}

def datacenterToRegion(availableDataCenter):
    if "bhs" in availableDataCenter: 
        return "canada"
    elif "vin" in availableDataCenter or "hil" in availableDataCenter:
        return "northamerica"
    else:
        return "europe"

if len(sys.argv) == 1:
    print(f"Loading catalog from {selectedEndpoint['catalog']}")
    catalogRaw = call(selectedEndpoint['catalog'])
    catalog = catalogRaw.json()
    catalogUnsorted = {}
    for plan in catalog['plans']:
        for price in plan['pricings']:
            if "installation" in price['capacities']: continue
            if price['interval'] != 1: continue
            catalogUnsorted[plan['planCode']] = {"price":int(price['price']),"plan":plan}

    catalogSorted = dict(sorted(catalogUnsorted.items(), key=lambda item: item[1]["price"]))

    for index, (planCode,data) in enumerate(catalogSorted.items()):
        if not "product" in data['plan']: continue
        print(index, data['plan']['invoiceName'])
    print("What plan do you want to buy? e.g 2 for KS-LE-B")

    lookup = input()
    for offerIndex, (planCode,data) in enumerate(catalogSorted.items()):
        if "product" in data['plan'] and offerIndex == int(lookup):
            planConfig['planCode'] = planCode
            for addon in data['plan']['addonFamilies']:
                if addon['mandatory'] != True: continue
                for index, option in enumerate(addon['addons']): print(index, option)
                print("Please select configuration")
                selected = input()
                for index, option in enumerate(addon['addons']):
                    if int(selected) == index: planConfig[addon['name']] = option
            break

    print("Loading availability...")
    availabilityRaw = call(f'{selectedEndpoint["availability"]}?excludeDatacenters=false&planCode={planConfig["planCode"]}&server={planConfig["planCode"]}')
    availability = availabilityRaw.json()
    print("Available in the following datacenters")
    if not availability:
        print(f"Failed to fetch availability, please enter the desired datacenters manualy.")
        planConfig['datacenter'] = input()
    else:
        for index, datacenter in enumerate(availability[0]['datacenters']):
            print(datacenter['datacenter'])
        print("Please enter the desired datacenter e.g waw you can also enter multiple like fra,gra,sbg")
        print("Keep in mind, they have to be in the same region.")
        planConfig['datacenter'] = input()

    planConfig['region'] = datacenterToRegion(planConfig['datacenter'])
    planConfig['endpoint'] = selectedEndpoint['endpointAPI']
print(f"Your selected config")
print(planConfig)
filename = f"{path}/plans/{planConfig['planCode']}-{planConfig['datacenter']}.json"
with open(filename, 'w') as f: json.dump(planConfig, f, indent=4)
print(f"Saved as {filename}")
time.sleep(2)

# Instantiate. Visit https://api.ovh.com/createToken/?GET=/me
# to get your credentials
client = ovh.Client(
    endpoint=selectedEndpoint['endpoint'],
    application_key=config['application_key'],
    application_secret=config['application_secret'],
    consumer_key=config['consumer_key'],
)

# Print nice welcome message
print("Welcome", client.get('/me')['firstname'])
availableDataCenter = "bhs"
retry = 0

while True:
    print("Preparing Package")
    #getting current time
    print("Getting Time")
    response = call(f"https://{selectedEndpoint['endpointAPI']}/1.0/auth/time")
    timeDelta = int(response.text) - int(time.time())
    # creating a new cart
    cart = client.post("/order/cart", ovhSubsidiary=config['ovhSubsidiary'], _need_auth=False)
    #assign new cart to current user
    client.post("/order/cart/{0}/assign".format(cart.get("cartId")))
    #putting KS-A into cart
    #result = client.post(f'/order/cart/{cart.get("cartId")}/eco',{"duration":"P1M","planCode":"22sk010","pricingMode":"default","quantity":1})
    #apparently this shit sends malformed json whatever baguette
    payload = {'duration':'P1M','planCode':planConfig['planCode'],'pricingMode':'default','quantity':1}
    call(f"https://{selectedEndpoint['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/eco", payload)
    #getting current cart
    response = call(f"https://{selectedEndpoint['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}")
    #modify item for checkout
    itemID = response.json()['items'][0]
    print(f'Getting current cart {cart.get("cartId")}')
    #set configurations
    configurations = [{'label':'region','value':planConfig['region']},{'label':'dedicated_datacenter','value':planConfig['datacenter']},{'label':'dedicated_os','value':'none_64.en'}]
    for entry in configurations:
        print(f"Setting {entry}")
        call(f"https://{selectedEndpoint['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/item/{itemID}/configuration",entry)
    #set options
    options = [{'itemId':itemID,'duration':'P1M','planCode':planConfig['bandwidth'],'pricingMode':'default','quantity':1},
            {'itemId':itemID,'duration':'P1M','planCode':planConfig['storage'],'pricingMode':'default','quantity':1},
            {'itemId':itemID,'duration':'P1M','planCode':planConfig['memory'],'pricingMode':'default','quantity':1}
    ]
    for option in options:
        print(f"Setting {option}")
        call(f"https://{selectedEndpoint['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/eco/options", option)
    print("Package ready, waiting for stock")
    #the order expires after about 1 day
    for check in range(70000):
        now = datetime.now()
        print(f'Run {check+1} {now.strftime("%H:%M:%S")}')
        #wait for stock
        try:
            response = requests.get(f'{selectedEndpoint["availability"]}?excludeDatacenters=false&planCode={planConfig["planCode"]}&server={planConfig["planCode"]}')
        except Exception as e:
            print(f"Failed to fetch stock got error '{e}' retrying...")
            time.sleep(2)
            continue
        if response.status_code == 200:
            stock = response.json()
            score = 0
            if not stock: 
                print(f"Unable to find {planConfig['planCode']} in availability.")
                time.sleep(randint(5,10))
                continue
            for configuration in stock:
                if configuration['memory'] != planConfig['memory'].replace(f"-{planConfig['planCode']}","") or configuration['storage'] != planConfig['storage'].replace(f"-{planConfig['planCode']}",""): continue
                for datacenter in configuration['datacenters']:
                    if datacenter['availability'] != "unavailable" and config['anyDatacenter']:
                        availableDataCenter = datacenter['datacenter'] 
                        score = score +1
                        break
                    elif datacenter['availability'] != "unavailable" and datacenter['datacenter'] in planConfig['datacenter']:
                        availableDataCenter = datacenter['datacenter'] 
                        score = score +1
                        break
        else:
            time.sleep(randint(5,10))
            continue
        #lets checkout boooyaaa
        if score >= 1:
            #autopay should be set to true if you want automatic delivery, otherwise it will just generate a invoice
            payload={'autoPayWithPreferredPaymentMethod':config['autoPay'],'waiveRetractationPeriod':config['autoPay']}
            #prepare sig
            target = f"https://{selectedEndpoint['endpointAPI']}/1.0/order/cart/{cart.get('cartId')}/checkout"
            now = str(int(time.time()) + timeDelta)
            signature = hashlib.sha1()
            signature.update("+".join([config['application_secret'], config['consumer_key'],'POST', target, json.dumps(payload), now]).encode('utf-8'))
            headers['X-Ovh-Signature'] = "$1$" + signature.hexdigest()
            headers['X-Ovh-Timestamp'] = now
            try:
                response = requests.post(target, headers=headers, data=json.dumps(payload))
                if response.status_code == 200:
                    print(response.status_code)
                    print(json.dumps(response.json(), indent=4))
                    exit("Done")
                else:
                    print("Got non 200 response code on checkout, retrying")
                    print(json.dumps(response.json(), indent=4))
                    retry += 1
                    if retry > 15: exit()
                    if retry % 4 == 0 and config['anyDatacenter']:
                        print(f"Switching Region to {datacenterToRegion(availableDataCenter)} and datacenter to {availableDataCenter}") 
                        planConfig['datacenter'] = availableDataCenter
                        planConfig['region'] = datacenterToRegion(availableDataCenter)
                        break
            except Exception as e:
                print(f"Unable to submit order got '{e}' as error")
                retry += 1
                if retry > 15: exit()
            time.sleep(2)
        else:
            time.sleep(1)