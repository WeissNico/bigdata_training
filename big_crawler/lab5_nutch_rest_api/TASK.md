

Description of Nutch RESTR API

https://docs.google.com/document/d/1OGg22ATohapP2ycewIaTcUnENc2FeyYzni0ED_Jjxz8/edit

curl http://159.122.175.139:30081/admin
curl -d '{"id": "12345","name": "doandodge","seedUrls": [{"id": 1,"seedList": null,"url": "http://www.region-suedostoberbayern.bayern.de/verbandsarbeit/sitzungen/"} ]}' -H "Content-Type: application/json" -X POST http://159.122.175.139:30081/seed/create




db.getCollection('webpage').find({'_id':  { $not: /^org\.apache\.nutch/}})
    