from flask import Flask, jsonify, request
import sklearn
import minio
import numpy as np


app = Flask(__name__)

@app.route('/service')
def service():
    return 'Notification Service',200

@app.route('/sendEmail',methods=["POST"])
def sendEmail():
  return jsonify({"Accepted":202}),202
    
        
if __name__ == '__main__':
	app.run(debug=True)