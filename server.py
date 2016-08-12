# Copyright 2016 Arne Johanson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import pandas as pd
from sklearn import preprocessing, cross_validation, linear_model, metrics
from flask import Flask, request, Response, jsonify, send_from_directory
import pickle


app = Flask(__name__, static_url_path="")
app.debug = False

t_reference = "2012-06-01T00:00:01Z"
dateOffset = np.datetime64(t_reference)

try:
	dataPath = "./data/"
	with open(dataPath+"features.pkl", "rb") as fp:
		features = pickle.load(fp)
	with open(dataPath+"labels.pkl", "rb") as fp:
		labels = pickle.load(fp)
	with open(dataPath+"lo_res_df.pkl", "rb") as fp:
		loResDF = pickle.load(fp)
	with open(dataPath+"hi_res_df.pkl", "rb") as fp:
		hiResDF = pickle.load(fp)
except:
	features = []
	labels = None
	loResDF = None
	hiResDF = None


def getServerErrorResponse(msg="Internal Server Error"):
	return Response(response=msg, status=500, mimetype="text/plain")

def getBadInputResponse(msg="Bad Request"):
	return Response(response=msg, status=400, mimetype="text/plain")


@app.route("/coral_analysis/static/<path>", methods=["GET"])
def getStaticFile(path):
	return send_from_directory("public", path)


@app.route("/coral_analysis/features", methods=["GET"])
def getFeatures():
	global features
	return jsonify({"features": features})


@app.route("/coral_analysis/observations", methods=["GET"])
def getObservations():
	global labels, t_reference, dateOffset
	if labels is None:
		return getServerErrorResponse()
	obsTS = list(map(lambda t,x: [int((t-dateOffset)/np.timedelta64(1, "s")), x], labels.index.values, labels.values))
	return jsonify({"data": obsTS, "t_reference": t_reference})


@app.route("/coral_analysis/model", methods=["GET"])
def getModel():
	global features, labels, loResDF, hiResDF, t_reference, dateOffset
	if labels is None or loResDF is None or hiResDF is None:
		return getServerErrorResponse()
	if not ("features" in request.args) or request.args["features"] == "":
		return getBadInputResponse()
	
	reqFeatures = request.args["features"].split(",")
	for f in reqFeatures:
		if not (f in features):
			return getBadInputResponse("Unknown Feature: {}".format(f))
	
	seed = None
	if "seed" in request.args:
		try:
			seed = int(request.args["seed"])
		except:
			pass
	
	
	X = loResDF.loc[:,reqFeatures].values
	y = labels.values
	X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, y, test_size=0.4, random_state=seed)

	scaler = preprocessing.StandardScaler()
	scaler.fit(X_train)
	X_train_std = scaler.transform(X_train)
	X_test_std = scaler.transform(X_test)

	classifier = linear_model.LogisticRegression(solver="liblinear", random_state=(2*seed) if not (seed is None) else None, penalty="l2", C=1.0)
	classifier.fit(X_train_std, y_train)

	predictions_test = classifier.predict(X_test_std)
	accuracy = metrics.accuracy_score(y_test, predictions_test)

	X_hiRes = hiResDF.loc[:,reqFeatures].values
	X_hiRes_std = scaler.transform(X_hiRes)
	p_prediction_hiRes = classifier.predict_proba(X_hiRes_std)[:,1]
	hiResTS = list(map(lambda t,x: [int((t-dateOffset)/np.timedelta64(1, "s")),x], hiResDF.index.values, p_prediction_hiRes))
	
	return jsonify({"features": reqFeatures,\
		"coefficients": classifier.coef_[0,:].tolist(),\
		"intercept": classifier.intercept_[0],\
		"accuracy_test": accuracy,\
		"t_reference": t_reference,\
		"p_prediction": hiResTS})



if __name__ == '__main__':
	#app.run(host='0.0.0.0')
	app.run(threaded=True, port=3340, use_debugger=False, use_reloader=False)
