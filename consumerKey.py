import json, ovh

with open('config.json') as f: config = json.load(f)
with open('endpoints.json') as f: endpoints = json.load(f)

print("Please select the endpoint for the catalog")
for index, option in enumerate(endpoints): print(index, option)
selected = input("Endpoint: ")
for index, option in enumerate(endpoints):
    if int(selected) == index: 
        selectedEndpoint = endpoints[option]['endpoint']
        break

# create a client using configuration
client = ovh.Client(
    endpoint=selectedEndpoint,
    application_key=config['application_key'],
    application_secret=config['application_secret']
)

# Request RO, /me API access
ck = client.new_consumer_key_request()
ck.add_recursive_rules(ovh.API_READ_WRITE, "/")

# Request token
validation = ck.request(allowedIPs=["0.0.0.0/0"])

print("Please visit %s to authenticate" % validation['validationUrl'])
input("and press Enter to continue...")

# Print nice welcome message
print("Welcome", client.get('/me')['firstname'])
print("Btw, your 'consumerKey' is '%s'" % validation['consumerKey'])