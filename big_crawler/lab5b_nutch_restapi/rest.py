from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route("/run", methods=['GET'])
def run():
    subprocess.call(["/sbin/start-stop-daemon","-b","--start","-v","/nutch/bin/run.sh"])
    return "Ok"

@app.route("/seed", methods=['POST','GET'])
def seed():
    seed_text = request.args.get('seed')
    file = open('/urls/seeds.txt','w')
    file.write(seed_text) 
    file.close() 
    return seed_text

@app.route("/update", methods=['GET'])
def update():
    #tbd -> load list from elastic and save it under /urls/seeds.txt
    return False

@app.route("/")
def home():
    return "<h1>Test</h1>"

if __name__ == "__main__":
    app.run(port=8081,host="0.0.0.0")

#https://www.google.de/search?q=überwachungsbericht+für+e-anlagen