
var caPlotColors = [
	"indianred",
	"darkcyan",
	"green",
	"orange",
	"maroon",
	"indigo",
	"gold",
	"darkkhaki",
	"blueviolet",
	"lightsalmon",
	"olive",
	"seagreen",
	"slategray",
	"crimson",
	"lime"
];
caCurrentColor = 0;

var caPlot = null;
var caFeatures = null;
var caObservations = null;
var caUniqueModelNames = [];

$(document).ready(function() {
	$.getJSON("/coral_analysis/features", function(data) {
		if(!data.hasOwnProperty("features")) {
			return;
		}
		caFeatures = data.features;
		if(caFeatures && caObservations) {
			initCAGUI();
		}
	});

	$.getJSON("/coral_analysis/observations", function(data) {
		if(!data.hasOwnProperty("data") || !data.hasOwnProperty("t_reference")) {
			return;
		}
		var t_ref = new Date(data.t_reference);
		caObservations = data.data.map(function(d) {
			var t = new Date(t_ref);
			t.setUTCSeconds(t.getUTCSeconds()+d[0]);
			return [t, d[1]];
		});
		if(caFeatures && caObservations) {
			initCAGUI();
		}
	});
});

function getCAPlotSize() {
	var margin = 100;
	var height2Width = 0.4;
	return [window.innerWidth-margin, Math.round(height2Width*(window.innerWidth-margin))];
}

function toggleAddModelButtons(disabled) {
	$("#buttonAddModel").prop("disabled", disabled);
	$("#buttonAddModel1F").prop("disabled", disabled);
	$("#buttonAddModel2F").prop("disabled", disabled);
	$("#buttonAddModel6F").prop("disabled", disabled);
}

function rightPadStr2Len(str, n) {
	if(str.length >= n) {
		return str;
	}
	return str+(" ".repeat(n-str.length));
}

function formatFloat(f) {
	return (f>=0 ? " "+f : f.toString());
}

function loadAndDisplayModel(features, seed) {
	$.ajax({
		url: "/coral_analysis/model?features="+features.join()+(seed && !isNaN(seed) ? "&seed="+seed : ""),
		type: "GET",
		cache: false,
		success: function(retdata) {
			toggleAddModelButtons(false);
			
			var t_ref = new Date(retdata.t_reference);
			retdata.p_prediction = retdata.p_prediction.map(function(d) {
				var t = new Date(t_ref);
				t.setUTCSeconds(t.getUTCSeconds()+d[0]);
				return [t, d[1]];
			});

			var modelName = "Model ("+(retdata.features.length<=2 ? retdata.featureNames.join("; ") : retdata.features.length+" Features")+")";
			var modelID = "model"+retdata.features.join();
			caPlot.addDataSet(modelID, modelName, retdata.p_prediction, caPlotColors[caCurrentColor], false);
			caCurrentColor = (caCurrentColor+1)%caPlotColors.length;
			caUniqueModelNames.push(modelID);

			padLen = 30;
			$("#CAModelStats").append('----------------------\n')
				.append('Model with '+retdata.features.length+' feature'+(retdata.features.length>1 ? "s" : "")+'\n')
				.append('Test accuracy: '+retdata.accuracy_test+'\n')
				.append('Overall accuracy: '+retdata.accuracy_overall+'\n')
				.append('Coefficients:\n')
				.append('  '+rightPadStr2Len("Intercept:", padLen)+' '+formatFloat(retdata.intercept)+'\n');
			retdata.features.forEach(function(f, i) {
				$("#CAModelStats").append('  '+rightPadStr2Len(retdata.featureNames[i]+":", padLen)+' '+formatFloat(retdata.coefficients[i])+'\n');
			});
			$("#CAModelStats").scrollTop($("#CAModelStats")[0].scrollHeight - $("#CAModelStats").height());
		},
		error: function() {
			toggleAddModelButtons(false);
		}
	});
}

function initCAGUI() {
	caFeatures.forEach(function(f) {
		$("#CAFeatureList").append('<li class="checkbox"><label><input type="checkbox" id="CABox_'+f.id+'"> '+f.name+'</label></li>');
	});
	
	caPlot = new CanvasTimeSeriesPlot(d3.select("#CAPlot"), getCAPlotSize(), {
		yAxisLabel: "p_Extension"
	});
	caPlot.setZoomYAxis(false);
	caPlot.addDataSet("observations", "Observations", caObservations, "steelblue", true);
	caDecisionBoundary = caObservations.map(function(d) {
		return [d[0], 0.5];
	});
	caPlot.addDataSet("boundary", "Decision Boundary", caDecisionBoundary, "black", false);
	caPlot.updateDomains(caPlot.calculateXDomain(), [-0.1, 1.1], false);

	$(window).resize(function() {
		caPlot.resize(getCAPlotSize());
	});

	$("#buttonClearFeatures").click(function() {
		caFeatures.forEach(function(f) {
			$("#CABox_"+f.id).prop("checked", false);
		});
	});

	$("#buttonClearModels").click(function() {
		$("#CAModelStats").empty();
		caUniqueModelNames.forEach(function(s) {
			caPlot.removeDataSet(s);
		});
		caUniqueModelNames = [];
	});

	$("#buttonAddModel1F").click(function() {
		toggleAddModelButtons(true);
		var modelSeed = parseInt($("#inputCASeed").val());
		loadAndDisplayModel(["dirUp_lag_3h_pc1"], modelSeed);
	});

	$("#buttonAddModel2F").click(function() {
		toggleAddModelButtons(true);
		var modelSeed = parseInt($("#inputCASeed").val());
		loadAndDisplayModel(["dirUp_lag_4h_pc1", "magUp_lag_2h_pc1"], modelSeed);
	});

	$("#buttonAddModel6F").click(function() {
		toggleAddModelButtons(true);
		var modelSeed = parseInt($("#inputCASeed").val());
		loadAndDisplayModel(["dirUp_lag_3h_pc1", "magUp_lag_2h_pc1", "dirUp_lag_4h_pc1", "magDown_lag_3h_pc2", "magDown_lag_3h_pc3", "magDown_lag_2h_pc2"], modelSeed);
	});

	$("#buttonAddModel").click(function() {
		toggleAddModelButtons(true);
		
		var modelFeatures = [];
		caFeatures.forEach(function(f) {
			if($("#CABox_"+f.id).is(":checked")) {
				modelFeatures.push(f.id);
			}
		});
		if(modelFeatures.length == 0) {
			toggleAddModelButtons(false);
			return;
		}

		var modelSeed = parseInt($("#inputCASeed").val());

		loadAndDisplayModel(modelFeatures, modelSeed);
	});
}
