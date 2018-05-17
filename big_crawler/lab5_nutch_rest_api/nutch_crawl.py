from nutch.nutch import Nutch
from nutch.nutch import SeedClient
from nutch.nutch import Server
from nutch.nutch import JobClient
import nutch

sv = Server('http://159.122.175.139:30081')
sc = SeedClient(sv)
seed_urls = ('http://espn.go.com', 'http://www.espn.com')
sd = sc.create('espn-seed', seed_urls)

nt = Nutch('default')
jc = JobClient(sv, 'test', 'default')
cc = nt.Crawl(sd, sc, jc)
while True:
    job = cc.progress()  # gets the current job if no progress, else iterates and makes progress
    if job == None:
        break