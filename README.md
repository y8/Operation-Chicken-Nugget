# Operation-Chicken-Nugget

Goal of this Operation is, grabbing a KS-A in BHS.<br />
**Don't run this on a VPS, you will get flagged for Fraud**<br />
**Make sure you configure it correctly, otherwise you end up getting a 500**

## Dependencies

```
pip3 install requests ovh
```

## Setup

1. Create an Application<br />
https://ca.api.ovh.com/createApp/<br />
https://eu.api.ovh.com/createApp/<br />

2. Put the keys into config.json<br />
Example how config.json should look like by now <br />

```
{
    "ovhSubsidiary":"CA",
    "application_key":"xxxxxxxxxx",
    "application_secret":"xxxxxxxxxxxxxxxxxx",
    "dedicated_datacenter":"fr",
    "region":"europe",
    "consumer_key":"",
    "switchRegion":false,
    "anyDatacenter":false,
    "autoPay":false
}
```

2. Request the consumerKey with running consumerKey.py and put it into config.json <br />

3. Edit nugget.py if you want to, by default no autopay, has to be enabled manually.<br />

4. Profit! <br />

## Donations

If you like the bot, you can do a small donation via Paypal: neo@tiefkuehler-madness.me