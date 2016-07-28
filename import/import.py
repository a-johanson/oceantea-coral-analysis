# Copyright (c) 2016 Arne Johanson

import numpy as np
import pandas as pd
from sklearn import decomposition
import json
import math
import pickle



### Load data

loadPrefix = "import/input/"

# Bins 1, 2, 3 of Up are to be removed later on
dirmagUpA = np.genfromtxt(loadPrefix+"MLM_adcpU_dirmag.csv", skip_header=3, delimiter=",", comments="#", dtype=float, invalid_raise=True)

# Bin 1 of Down is to be removed later on
dirmagDownA = np.genfromtxt(loadPrefix+"MLM_adcpD_dirmag.csv", skip_header=3, delimiter=",", comments="#", dtype=float, invalid_raise=True)

openessA = np.genfromtxt(loadPrefix+"coral_frames2.csv", skip_header=2, delimiter=",", comments="#", dtype=float, invalid_raise=True)


with open(loadPrefix+"scalar_POS434-156_conservativeTemperature_215_original.json") as fp:
	ctA = np.asarray(json.load(fp)["data"])

with open(loadPrefix+"scalar_POS434-156_absoluteSalinity_215_original.json") as fp:
	saA = np.asarray(json.load(fp)["data"])
	
with open(loadPrefix+"scalar_POS434-156_potentialDensityAnomaly_215_original.json") as fp:
	sigma0A = np.asarray(json.load(fp)["data"])



### Create time series date indices

dateOffset = np.datetime64("2012-06-01T00:00:01Z")

hiResIndexStart = 336185 # in [s]
hiResIndexEnd = 1342685 # in [s] --- shorter: 1342685 --- longer: 9332570
hiResIndexStep = 600 # in [s]
hiResIndex = dateOffset + np.arange(hiResIndexStart, hiResIndexEnd, hiResIndexStep).astype("timedelta64[s]")

ignoreBecauseOfLags = 7
loResIndex = dateOffset + openessA[ignoreBecauseOfLags:,0].astype("timedelta64[s]")

ctIndex = dateOffset + ctA[:,0].astype("timedelta64[s]")
saIndex = dateOffset + saA[:,0].astype("timedelta64[s]")
sigma0Index = dateOffset + sigma0A[:,0].astype("timedelta64[s]")

dirmagUpIndex = dateOffset + dirmagUpA[:,0].astype("timedelta64[s]")
dirmagDownIndex = dateOffset + dirmagDownA[:,0].astype("timedelta64[s]")


### Create original time series / data frames

ctOrig = pd.Series(ctA[:,1], index=ctIndex)
saOrig = pd.Series(saA[:,1], index=saIndex)
sigma0Orig = pd.Series(sigma0A[:,1], index=sigma0Index)

nBinsUnfilteredUp = round((dirmagUpA.shape[1]-1)/2)
dirUpOrig = pd.DataFrame(data=dirmagUpA[:,1:(1+nBinsUnfilteredUp)], index=dirmagUpIndex)
magUpOrig = pd.DataFrame(data=dirmagUpA[:,(1+nBinsUnfilteredUp):], index=dirmagUpIndex)

nBinsUnfilteredDown = round((dirmagDownA.shape[1]-1)/2)
dirDownOrig = pd.DataFrame(data=dirmagDownA[:,1:(1+nBinsUnfilteredDown)], index=dirmagDownIndex)
magDownOrig = pd.DataFrame(data=dirmagDownA[:,(1+nBinsUnfilteredDown):], index=dirmagDownIndex)


### Create target products

loResDF = pd.DataFrame(index=loResIndex, dtype=np.float64)
hiResDF = pd.DataFrame(index=hiResIndex, dtype=np.float64)

labels = pd.Series(openessA[ignoreBecauseOfLags:,1], index=loResIndex, dtype=np.float64)

#loResDF.loc[:,"f1"] = labels#pd.Seriesnp.random(loResDF.index.size)
#print(loResDF)

#assert False


### Interpolate univariate time series

def interpolateUnivariateTSLinear(targetTSIndex, sourceTS, offset=np.timedelta64(0, "s"), derivative=False):
	target_index = targetTSIndex + offset
	indexAfter = np.searchsorted(sourceTS.index.values, target_index, side="right")
	value_a = sourceTS.values[indexAfter-1]
	value_b = sourceTS.values[indexAfter]
	time_a = sourceTS.index.values[indexAfter-1]
	time_b = sourceTS.index.values[indexAfter]
	t_span = time_b - time_a
	target_values = np.empty(target_index.shape[0])
	if not derivative:
		weight_b = (target_index - time_a) / t_span
		target_values[:] = (1-weight_b) * value_a + weight_b * value_b
	else:
		t_span_in_minutes = t_span / np.timedelta64(1, "m")
		target_values[:] = (value_b - value_a) / t_span_in_minutes
	return pd.Series(data=target_values, index=targetTSIndex) 


def addUnivariateProductsToDF(df, targetName, targetTSIndex, sourceTS, offsetsInMin=[-2*60, -3*60, -4*60]):
	# interpolation
	name = targetName
	df.loc[:,name] = interpolateUnivariateTSLinear(targetTSIndex, sourceTS)

	# lags
	for lag in offsetsInMin:
		name = "{}_lag_{}min".format(targetName, abs(lag))
		df.loc[:,name] = interpolateUnivariateTSLinear(targetTSIndex, sourceTS, offset=np.timedelta64(lag, "m"))



print("k =", labels.shape[0])

addUnivariateProductsToDF(loResDF, "ct", loResIndex, ctOrig)
addUnivariateProductsToDF(hiResDF, "ct", hiResIndex, ctOrig)
addUnivariateProductsToDF(loResDF, "sa", loResIndex, saOrig)
addUnivariateProductsToDF(hiResDF, "sa", hiResIndex, saOrig)
addUnivariateProductsToDF(loResDF, "sigma0", loResIndex, sigma0Orig)
addUnivariateProductsToDF(hiResDF, "sigma0", hiResIndex, sigma0Orig)

#print(hiResDF)
#assert False



### Interpolate multivariate time series

def interpolateMultivariateTSLinear(targetTSIndex, sourceDF, colPrefix, colOffset=0, offset=np.timedelta64(0, "s"), derivative=False, angles=False):
	target_index = targetTSIndex + offset
	indexAfter = np.searchsorted(sourceDF.index.values, target_index, side="right")
	time_a = sourceDF.index.values[indexAfter-1]
	time_b = sourceDF.index.values[indexAfter]
	t_span = time_b - time_a
	target_values = np.empty((target_index.shape[0], (2 if angles and not derivative else 1)*(sourceDF.values.shape[1]-colOffset)))
	for j in range(colOffset, sourceDF.values.shape[1]):
		value_a = sourceDF.values[indexAfter-1, j]
		value_b = sourceDF.values[indexAfter  , j]
		if not derivative:
			weight_b = (target_index - time_a) / t_span
			weight_a = 1 - weight_b
			if not angles:
				target_values[:,j-colOffset] = weight_a * value_a + weight_b * value_b
			else:
				#target.values[:,j-colOffset] = np.arctan2(weight_a*np.sin(value_a) + weight_b*np.sin(value_b), \
				#								weight_a*np.cos(value_a) + weight_b*np.cos(value_b))
				interpolated_x = weight_a*np.cos(value_a) + weight_b*np.cos(value_b)
				interpolated_y = weight_a*np.sin(value_a) + weight_b*np.sin(value_b)
				interpolated_norm = np.sqrt(np.square(interpolated_x) + np.square(interpolated_y))
				target_values[:,(2*(j-colOffset))  ] = interpolated_x / interpolated_norm
				target_values[:,(2*(j-colOffset)+1)] = interpolated_y / interpolated_norm
		else:
			t_span_in_minutes = t_span / np.timedelta64(1, "m")
			if not angles:
				target_values[:,j-colOffset] = (value_b - value_a) / t_span_in_minutes
			else:
				#atan2(sin(x-y), cos(x-y))
				angle_diff = value_b - value_a
				target_values[:,j-colOffset] = np.arctan2(np.sin(angle_diff), np.cos(angle_diff)) / t_span_in_minutes
	return target_values


def addDataAndPCA(df, newPCAs, data, name, targetTSIndex, pcas, nComponents):
	if not pcas or not (name in pcas):
		pca = decomposition.PCA(n_components=nComponents, whiten=False)
		newPCAs[name] = pca
		pca.fit(data)
	else:
		pca = pcas[name]
	dataTransformed = pca.transform(data)
	for i in range(dataTransformed.shape[1]):
		df.loc[:,"{}_pc{}".format(name, i+1)] = pd.Series(data=dataTransformed[:,i], index=targetTSIndex)


def addMultivariateProductsToDF(df, targetName, targetTSIndex, sourceDF, pcas=None, nComponents=1, colOffset=0, angles=False, offsetsInMin=[-2*60, -3*60, -4*60]):
	# interpolation
	newPCAs = {}

	name = targetName
	data = interpolateMultivariateTSLinear(targetTSIndex, sourceDF, name, colOffset=colOffset, angles=angles)
	addDataAndPCA(df, newPCAs, data, name, targetTSIndex, pcas, nComponents)

	# lags
	for lag in offsetsInMin:
		name = "{}_lag_{}min".format(targetName, abs(lag))
		data = interpolateMultivariateTSLinear(targetTSIndex, sourceDF, name, colOffset=colOffset, angles=angles, offset=np.timedelta64(lag, "m"))
		addDataAndPCA(df, newPCAs, data, name, targetTSIndex, pcas, nComponents)
	
	return newPCAs

# filter out Bins 1-3 for upward-facing ADCP
nBinsSkipUp = 3

dirUpPCAs = addMultivariateProductsToDF(loResDF, "dirUp", loResIndex, dirUpOrig, nComponents=1, colOffset=nBinsSkipUp, angles=True)
addMultivariateProductsToDF(hiResDF, "dirUp", hiResIndex, dirUpOrig, pcas=dirUpPCAs, colOffset=nBinsSkipUp, angles=True)

magUpPCAs = addMultivariateProductsToDF(loResDF, "magUp", loResIndex, magUpOrig, nComponents=1, colOffset=nBinsSkipUp)
addMultivariateProductsToDF(hiResDF, "magUp", hiResIndex, magUpOrig, pcas=magUpPCAs, colOffset=nBinsSkipUp)


# filter out Bin 1 for downward-facing ADCP
nBinsSkipDown = 1

dirDownPCAs = addMultivariateProductsToDF(loResDF, "dirDown", loResIndex, dirDownOrig, nComponents=3, colOffset=nBinsSkipDown, angles=True)
addMultivariateProductsToDF(hiResDF, "dirDown", hiResIndex, dirDownOrig, pcas=dirDownPCAs, colOffset=nBinsSkipDown, angles=True)

magDownPCAs = addMultivariateProductsToDF(loResDF, "magDown", loResIndex, magDownOrig, nComponents=3, colOffset=nBinsSkipDown)
addMultivariateProductsToDF(hiResDF, "magDown", hiResIndex, magDownOrig, pcas=magDownPCAs, colOffset=nBinsSkipDown)



### Output data products

outputPrefix = "data/"

labels.to_pickle(outputPrefix+"labels.pkl")
loResDF.to_pickle(outputPrefix+"lo_res_df.pkl")
hiResDF.to_pickle(outputPrefix+"hi_res_df.pkl")

with open(outputPrefix+"features.pkl", "wb") as fp:
	pickle.dump(loResDF.columns.values.tolist(), fp)

print("Output files written")
