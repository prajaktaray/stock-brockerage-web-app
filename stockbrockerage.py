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
from flask import Response
import datetime as dt

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


class User(db.Model):
    __tablename__='auser'
    username = db.Column(db.String(80),primary_key=True)
    password=db.Column(db.String(80))
    email=db.Column(db.String(80))
    address=db.Column(db.String(80))

    def _init_(self,username,password,email,address):
        self.username = username
        self.password = password
        self.email = email
        self.address = address

    def _repr_(self):
        return f"{self.username} {self.password} is succesfully registered"

def token_verfication(token):
	s = TimedJSONWebSignatureSerializer(secret_key)
	try:
		data = s.loads(token)
	except SignatureExpired:
		print("SignatureExpired")
		return "expired"
	except BadSignature:
		print("Invalid Signature")
		return "invalid"
	username = data['id']
	username = username[3:-3]
	return username

@app.route("/allStocks", methods=['GET'])
@cross_origin()
@gzipped
def allCompanyStocks():
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	r = requests.get(url = "http://localhost:5002/allStocks")
	data = r.json()
	return jsonify(data)

@app.route('/data')
def names():
    data = {"names": ["John", "Jacob", "Julie", "Jennifer"]}
    return jsonify(data)

@app.route("/verfication",methods = ['POST'])
@cross_origin()
def verifyToken():
	data = request.json
	token = data['token']
	s = TimedJSONWebSignatureSerializer(secret_key)
	try:
		data = s.loads(token)
	except SignatureExpired:
		print("SignatureExpired")
		return jsonify({"Message":"Expired Token"})
	except BadSignature:
		print("Invalid Signature")
		return jsonify({"Message":"Invalid Token"})
	return jsonify({"Message":"Verified Token"})

@app.route("/login",methods = ['POST'])
@cross_origin()
@gzipped
def login():
	try:
		if request.method == "POST":
			data = request.json
			username = data['username']
			password = data['password']
			print("Getting Data from DB")
			user_data = User.query.filter_by(username=username).first()
			if user_data is None:
				print("Incorrect Credentials, Login failed")
				return jsonify({"message":"Login Failed"})
			if user_data.username == username:
				print("Matched Perfectly authenticated")
				s = TimedJSONWebSignatureSerializer(secret_key, expires_in = 100)
				token_input = "foo"+username+"bar"
				token = s.dumps({"id":token_input})
			return jsonify({"message":"authenticated","token":token,"username":username})
	except Exception as e:
		print(e.args)




@app.route('/registerUser',methods = ['POST'])
@cross_origin()
def save_user_details():
    try:
        if request.method == "POST":
            data = request.json
            print(data)
            username = data['username']
            password = data['password']
            email = data['email']
            address = data['address']
        user_insert=User(username = username,password = password,email = email,address = address)
        db.session.add(user_insert)
        db.session.commit()
        data={"message":"successfully Registered!","status":"success"}
        return jsonify(data)
    except Exception as e:
        print(e.args)
    print("getting the post request!")


class  UserTransaction(db.Model):
	__tablename__ = 'user_transcation'
	id = db.Column(db.String, primary_key=True)
	symbol = db.Column(db.String)
	username = db.Column(db.String(100))
	price = db.Column(db.Float)
	quantity = db.Column(db.Integer)
	last_purchased_dt = db.Column(db.Date)

	def __init__(self, symbol, username, price, quantity,last_purchased_dt,id):
		self.symbol = symbol
		self.username = username
		self.price = price
		self.quantity = quantity
		self.last_purchased_dt = last_purchased_dt
		self.id = id
	#def __repr__(self):
	#	return f"symbol :{self.symbol},username:{self.username},price:{self.price},quantity:{self.quantity},last_purchased_dt:{self.last_purchased_dt},id:{self.id}"

	def serialize(self):
		return {
			'symbol': self.symbol,
			'username': self.username,
			'price': self.price,
			'quantity':self.quantity,
			'last_purchased_dt' :self.last_purchased_dt,
			'id' : self.id
		}
	

class  UserProfile(db.Model):
	__tablename__ = 'stockuser'
	address = db.Column(db.String)
	email = db.Column(db.String)
	username = db.Column(db.String,primary_key=True)
	bankaccount1 = db.Column(db.String)
	bankaccount2 = db.Column(db.String)
	balance1 = db.Column(db.Float)
	balance2 = db.Column(db.Float)

	def __init__(self, address, username, email, bankaccount1,bankaccount2,balance1,balance2):
		self.address = address
		self.username = username
		self.email = email
		self.bankaccount1 = bankaccount1
		self.bankaccount2 = bankaccount2
		self.balance1 = balance1
		self.balance2 = balance2

	def __repr__(self):
		return f"address :{self.address},username:{self.username},email:{self.email},bankaccount1:{self.bankaccount1},bankaccount2:{self.bankaccount2},balance1:{self.balance1},balance2:{self.balance2}"

	def serialize(self):
		return {
			'address': self.address,
			'username': self.username,
			'email': self.email,
			'bankaccount1':self.bankaccount1,
			'bankaccount2' :self.bankaccount2,
			'balance1' : self.balance1,
			'balance2' : self.balance2
		}
@app.route("/findUserTransaction", methods=["GET"])
@cross_origin()
def findUserTransaction():
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	username = status
	userTran = UserTransaction.query.filter_by(username=username).all()
	print(userTran)
	return jsonify(usertrans=[e.serialize() for e in userTran])

@app.route('/buyStock',methods=['POST'])
@cross_origin()
def buyStock():
	try:
		token = request.headers.get('token')
		status = token_verfication(token)
		if status == "expired":
			return jsonify({"message":"Token Expired!"})
		elif status == "invalid":
			return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
		currentHour = dt.datetime.now().hour
		#if currentHour<0 or currentHour>24:
		if currentHour<8 or currentHour>17:
			data ={"message": "Beyond Working Hours"}
			return jsonify(data)
		print("abc")
		print(request.method)
		if request.method == "POST":
			print("I am here")
			data = request.json
			username = status
			symbol = data["symbol"]
			id = username+"_"+symbol
			quantity = data["quantity"]
			price = float(data["price"])
			last_purchased_dt = dt.datetime.now()

		userProfile = UserProfile.query.get(username)
		print(userProfile)
		act_balance1=userProfile.balance1
		total_price=price*quantity
		if act_balance1<total_price:
			print("Insufficient Balance")
			add_balance=total_price-act_balance1
			print("Balance added")
			act_balance1=act_balance1+add_balance
		balance_remain = act_balance1-total_price
		userTran = UserTransaction.query.get(id)
		if userTran.id ==None:
			user_insert = UserTransaction(symbol=symbol, username=username, price=price, quantity=quantity,last_purchased_dt=last_purchased_dt,id=id)
			db.session.add(user_insert)
			db.session.commit()
		else:
			userTran.quantity= userTran.quantity+quantity
			db.session.commit()
		userProfile.balance1=balance_remain
		db.session.commit()
		data = {"message":"Buy Success"}
		return jsonify(data)
	except Exception as e:
		print(e.args)

@app.route('/sellStock',methods=['POST'])
@cross_origin()
def sellStock():
	try:
		token = request.headers.get('token')
		status = token_verfication(token)
		if status == "expired":
			return jsonify({"message":"Token Expired!"})
		elif status == "invalid":
			return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
		currentHour = dt.datetime.now().hour
		#if currentHour<0 or currentHour>24:
		if currentHour<8 or currentHour>17:
			data ={"message": "Beyond Working Hours"}
			return jsonify(data)
		print("abc")
		print(request.method)
		if request.method == "POST":
			print("I am here")
			data = request.json
			username = status
			symbol = data["symbol"]
			id = username+"_"+symbol
			quantity = data["quantity"]
			price = float(data["price"])
			last_purchased_dt = dt.datetime.now()

		userProfile = UserProfile.query.get(username)
		print(userProfile)
		act_balance1=userProfile.balance1
		total_price=price*quantity

		balance_remain = act_balance1+total_price
		userTran = UserTransaction.query.get(id)
		if quantity>userTran.quantity:
			data = {"message":"Insufficient Quantity"}
			return jsonify(data)

		if userTran.id ==None:
			user_insert = UserTransaction(symbol=symbol, username=username, price=price, quantity=quantity,last_purchased_dt=last_purchased_dt,id=id)
			db.session.add(user_insert)
			db.session.commit()
		else:
			userTran.quantity= userTran.quantity-quantity
			db.session.commit()
		userProfile.balance1=balance_remain
		db.session.commit()
		data = {"message":"Sell Success "}
		return jsonify(data)
	except Exception as e:
		print(e.args)
	print("Success Post")
	
@app.route("/getUser", methods=["GET"])
@cross_origin()
def getUserData():
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	print("Inside getUser")
	print(status)
	username = status
	user_data = UserProfile.query.filter_by(username=username).first()
	if user_data is None:
		print("user data not found")
		return jsonify({"message":"User Data Not Found"})
	else:
	    return jsonify({"address":user_data.address,"username":user_data.username,"email":user_data.email,"bankaccount1":user_data.email,"bankaccount2":user_data.bankaccount2,"balance1":user_data.balance1,"balance2":user_data.balance2})
@app.route('/UpdateUserProfile',methods=['POST'])
@cross_origin()
def updateUserProfile():
	try:
		token = request.headers.get('token')
		status = token_verfication(token)
		if status == "expired":
			return jsonify({"message":"Token Expired!"})
		elif status == "invalid":
			return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
		if request.method == "POST":
			print("I am here")
			data = request.json
			username = status
			address = data["address"]
			email = data["email"]
			bankaccount1 = data["bankaccount1"]
			bankaccount2 = data["bankaccount2"]
			balance1 = data["balance1"]
			balance2 = data["balance2"]
		print(status)
		print(username)
		userProfile=UserProfile.query.filter_by(username=username).first()
		print(userProfile)
		if userProfile ==None:
			print("Inside None")
			user_insert = UserTransaction(username=username,email=email,bankaccount1=bankaccount1,bankaccount2=bankaccount2,balance1=balance1,balance2=balance2)
			db.session.add(user_insert)
			db.session.commit()
			data = {"message":"User Inserted"}
			return jsonify(data)
		else:
			# userProfile.username = username
			# userProfile.address = address
			# userProfile.email = email
			# userProfile.bankaccount1 = bankaccount1
			# userProfile.bankaccount2 = bankaccount2
			# userProfile.balance1 = balance1
			# userProfile.balance2 = balance2
			UserProfile.query.filter_by(username=username).update(dict(username=username,email=email,bankaccount1=bankaccount1,bankaccount2=bankaccount2,balance1=balance1,balance2=balance2))
			db.session.commit()
			data = {"message":"User Updated"}
			# print(json.dumps(userProfile))
			return jsonify({"username":username,"email":email,"bankaccount1":bankaccount1,"bankaccount2":bankaccount2,"balance1":balance1,"balance2":balance2})
	except Exception as e:
		print(e.args)
	print("Success Post")
	
#Current week	
@app.route("/companyStockHistory/currentWeek/<company_symbol>", methods=["GET"])
@cross_origin()
def stockHistCurrWeek(company_symbol):
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	from weekHelper import getCurrentWeek,getDateRange
	FUNC="TIME_SERIES_DAILY"

	PARAMS = {'function':FUNC,
			  'apikey': apikey,
			  'symbol':company_symbol
			  }
	try:
		response = requests.get(url=URL,params=PARAMS)
	except requests.ConnectionError:
		return "ConnectionError"
	jresponse = response.text
	#output_dict={}

	temp_li=[]
	today = datetime.datetime.now()
	new_date=today.strftime('%Y-%m-%d')
	start_date , end_date = getCurrentWeek(new_date)
	input_dict = json.loads(jresponse)
	for single_date in getDateRange(start_date,end_date):
		if single_date in input_dict['Time Series (Daily)']:
			temp_dict={}
			temp_dict["date"] = single_date
			value = dict(list(input_dict['Time Series (Daily)'][single_date].items())[0:1])
			val=list(value.items())[0][1]
			temp_dict["price"] = val
			temp_li.append(temp_dict)
	return jsonify(temp_li)
	
#Past week
@app.route("/companyStockHistory/currentDay/<company_symbol>", methods=["GET"])
@cross_origin()
def stockHistory(company_symbol):
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	interval=config['COMPANY']['interval']
	FUNC="TIME_SERIES_INTRADAY"

	PARAMS = {'function':FUNC,
			  'apikey': apikey,
			  'interval': interval,
			  'symbol':company_symbol
			  }
	try:
		response = requests.get(url=URL,params=PARAMS)
	except requests.ConnectionError:
		return "ConnectionError"
	jresponse = response.text
	temp_li=[]
	today = str(date.today())
	input_dict = json.loads(jresponse)
	input_dict=input_dict['Time Series (1min)']
	for i in input_dict:
		#print(i)
	    temp_dict={}
	    temp_dict["date"] = i
	    value = dict(list(input_dict[i].items())[0:1])
	    val=list(value.items())[0][1]
	    temp_dict["price"] = val
	    temp_li.append(temp_dict)
	    #print(value)
	#data1 = response.json()
	return jsonify(temp_li)
@app.route("/companyStockHistory/currentWeek/<company_symbol>", methods=["GET"])
@cross_origin()
def stockHistCurrWeek(company_symbol):
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	from weekHelper import getCurrentWeek,getDateRange
	FUNC="TIME_SERIES_DAILY"

	PARAMS = {'function':FUNC,
			  'apikey': apikey,
			  'symbol':company_symbol
			  }
	try:
		response = requests.get(url=URL,params=PARAMS)
	except requests.ConnectionError:
		return "ConnectionError"
	jresponse = response.text
	#output_dict={}

	temp_li=[]
	today = datetime.datetime.now()
	new_date=today.strftime('%Y-%m-%d')
	start_date , end_date = getCurrentWeek(new_date)
	input_dict = json.loads(jresponse)
	for single_date in getDateRange(start_date,end_date):
		if single_date in input_dict['Time Series (Daily)']:
			temp_dict={}
			temp_dict["date"] = single_date
			value = dict(list(input_dict['Time Series (Daily)'][single_date].items())[0:1])
			val=list(value.items())[0][1]
			temp_dict["price"] = val
			temp_li.append(temp_dict)
	return jsonify(temp_li)
	
#Past week
@app.route("/companyStockHistory/pastWeek/<company_symbol>", methods=["GET"])
@cross_origin()
def stockHistPastWeek(company_symbol):
	from weekHelper import getPastWeek,getDateRange
	FUNC="TIME_SERIES_DAILY"

	PARAMS = {'function':FUNC,
			  'apikey': apikey,
			  'symbol':company_symbol
			  }
	try:
		response = requests.get(url=URL,params=PARAMS)
	except requests.ConnectionError:
		return "ConnectionError"
	jresponse = response.text
	#output_dict={}

	temp_li=[]
	today = datetime.datetime.now()
	#new_date=today.strftime('%Y-%m-%d')
	start_date , end_date = getPastWeek(today)
	input_dict = json.loads(jresponse)
	for single_date in getDateRange(start_date,end_date):
		if single_date in input_dict['Time Series (Daily)']:
			temp_dict={}
			temp_dict["date"] = single_date
			value = dict(list(input_dict['Time Series (Daily)'][single_date].items())[0:1])
			val=list(value.items())[0][1]
			temp_dict["price"] = val
			temp_li.append(temp_dict)
	return jsonify(temp_li)


#MTD
@app.route("/companyStockHistory/MTD/<company_symbol>/<month_selected>", methods=["GET"])
@cross_origin()
def stockHistMonth(company_symbol,month_selected):
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	FUNC="TIME_SERIES_MONTHLY"

	PARAMS = {'function':FUNC,
			  'apikey': apikey,
			  'symbol':company_symbol
			  }
	try:
		response = requests.get(url=URL,params=PARAMS)
	except requests.ConnectionError:
		return "ConnectionError"
	jresponse = response.text
	temp_li=[]
	month = month_selected
	input_dict = json.loads(jresponse)
	for single_date in input_dict['Monthly Time Series']:

		if single_date >= month:
			output_dict={}
			output_dict["date"]=single_date
			value = dict(list(input_dict['Monthly Time Series'][single_date].items())[0:1])
			val = list(value.items())[0][1]
			output_dict["price"]= val
			temp_li.append(output_dict)

	return jsonify(temp_li)

#YTD
@app.route("/companyStockHistory/YTD/<company_symbol>/<year_selected>", methods=["GET"])
@cross_origin()
def stockHistYear(company_symbol,year_selected):
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	FUNC="TIME_SERIES_MONTHLY"

	PARAMS = {'function':FUNC,
			  'apikey': apikey,
			  'symbol':company_symbol
			  }
	try:
		response = requests.get(url=URL,params=PARAMS)
	except requests.ConnectionError:
		return "ConnectionError"
	jresponse = response.text

	temp_li=[]
	year = year_selected
	input_dict = json.loads(jresponse)
	for single_date in input_dict['Monthly Time Series']:
		if single_date >= year:
			output_dict={}
			output_dict["date"]=single_date
			value = dict(list(input_dict['Monthly Time Series'][single_date].items())[0:1])
			val = list(value.items())[0][1]
			output_dict["price"]= val
			temp_li.append(output_dict)
	return jsonify(temp_li)

#5years
@app.route("/companyStockHistory/fiveYears/<company_symbol>", methods=["GET"])
@cross_origin()
def stockFiveHistYear(company_symbol):
	token = request.headers.get('token')
	status = token_verfication(token)
	if status == "expired":
		return jsonify({"message":"Token Expired!"})
	elif status == "invalid":
		return Response("{'message':'Token Invalid'}", status=401, mimetype='application/json')
	FUNC="TIME_SERIES_MONTHLY"

	PARAMS = {'function':FUNC,
			  'apikey': apikey,
			  'symbol':company_symbol
			  }
	try:
		response = requests.get(url=URL,params=PARAMS)
	except requests.ConnectionError:
		return "ConnectionError"
	jresponse = response.text

	temp_li=[]
	year = "2014-12-06"
	input_dict = json.loads(jresponse)
	for single_date in input_dict['Monthly Time Series']:
		if single_date >= year:
			output_dict={}
			output_dict["date"]=single_date
			value = dict(list(input_dict['Monthly Time Series'][single_date].items())[0:1])
			val = list(value.items())[0][1]
			output_dict["price"]= val
			temp_li.append(output_dict)
	return jsonify(temp_li)


if __name__ =="__main__":
	app.run(host='localhost',port='5001',debug = True)
