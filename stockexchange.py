from flask import Flask,jsonify,request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine.url import URL
import requests
import simplejson
import json
import collections
#from datetime import date,timedelta,datetime
import datetime
from datetime import timedelta
from datetime import date
import configparser
from flask_migrate import Migrate
import random
from flask_cors import CORS,cross_origin
from itsdangerous import JSONWebSignatureSerializer,BadSignature,SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer
from flask_compress import Compress
import gzip, functools
from io import BytesIO as IO
from flask import after_this_request, request

URL = "http://ec2-18-222-112-169.us-east-2.compute.amazonaws.com/allStocks"
config = configparser.ConfigParser()
config.sections()
config.read('data/input.ini')
apikey=config['COMPANY']['apikey']
URL=config['COMPANY']["STOCK_URL"]
secret_key = config['COMPANY']["SECRET_KEY"]
database_uri = 'postgresql+psycopg2://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
	dbuser="postgres",
	dbpass="admin123$",
	dbhost="stockdb.cdbtubbb3y94.us-east-2.rds.amazonaws.com",
	dbname="postgres"
)

expiration_time = 600
app = Flask(__name__)
#CORS(app)
COMPRESS_MIMETYPES = ["text/html","text/css","text/xml","application/json"]
Compress(app)
app.config.update(
	SQLALCHEMY_DATABASE_URI=database_uri,
	SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
# initialize the database connection
db = SQLAlchemy(app)
URL = "http://ec2-18-222-112-169.us-east-2.compute.amazonaws.com/allStocks"

def gzipped(f):
    @functools.wraps(f)
    def view_func(*args, **kwargs):
        @after_this_request
        def zipper(response):
            accept_encoding = request.headers.get('Accept-Encoding', '')

            if 'gzip' not in accept_encoding.lower():
                return response

            response.direct_passthrough = False

            if (response.status_code < 200 or
                response.status_code >= 300 or
                'Content-Encoding' in response.headers):
                return response
            gzip_buffer = IO()
            gzip_file = gzip.GzipFile(mode='wb',
                                      fileobj=gzip_buffer)
            gzip_file.write(response.data)
            gzip_file.close()

            response.data = gzip_buffer.getvalue()
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Vary'] = 'Accept-Encoding'
            response.headers['Content-Length'] = len(response.data)

            return response

        return f(*args, **kwargs)

    return view_func

@app.route("/allStocks", methods=['GET'])
@cross_origin()
@gzipped
def allCompanyStocks():
	r = requests.get(url = URL)
	data = r.json()
	data1 = data["stock_data"]
	for i in range(len(data1)):
		data["stock_data"][i]["price"] = data1[i]["price"]+ random.randrange(-5,10)
	return jsonify(data)


if __name__ =="__main__":
	app.run(host='localhost',port='5002',debug = True)
