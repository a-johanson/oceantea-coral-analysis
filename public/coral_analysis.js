
var caPlotColors = [
	"orange",
	"maroon",
	"green",
	"indigo",
	"gold",
	"indianred",
	"darkcyan",
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

function toggleAddModelButton(disabled) {
	if(disabled) {
		$("#buttonAddModel").prop("disabled", true)
			.empty()
			.append('<span class="fa fa-spinner fa-pulse"></span> Retrieving...');
	}
	else {
		$("#buttonAddModel").prop("disabled", false)
			.empty()
			.append('Add Model');
	}
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
			toggleAddModelButton(false);
			
			var t_ref = new Date(retdata.t_reference);
			retdata.p_prediction = retdata.p_prediction.map(function(d) {
				var t = new Date(t_ref);
				t.setUTCSeconds(t.getUTCSeconds()+d[0]);
				return [t, d[1]];
			});

			var modelName = "Model ("+(features.length<=3 ? features.join(", ") : features.length+" Features")+")";
			var modelID = "model"+features.join();
			caPlot.addDataSet(modelID, modelName, retdata.p_prediction, caPlotColors[caCurrentColor], false);
			caCurrentColor = (caCurrentColor+1)%caPlotColors.length;
			caUniqueModelNames.push(modelID);

			padLen = 25;
			$("#CAModelStats").append('----------------------\n')
				.append('Model with '+features.length+' features\n')
				.append('Test accuracy: '+retdata.accuracy_test+'\n')
				.append('Coefficients:\n')
				.append('  '+rightPadStr2Len("Intercept:", padLen)+' '+formatFloat(retdata.intercept)+'\n');
			retdata.features.forEach(function(f, i) {
				$("#CAModelStats").append('  '+rightPadStr2Len(f+":", padLen)+' '+formatFloat(retdata.coefficients[i])+'\n');
			});
			$("#CAModelStats").scrollTop($("#CAModelStats")[0].scrollHeight - $("#CAModelStats").height());
		},
		error: function() {
			toggleAddModelButton(false);
		}
	});
}

function initCAGUI() {
	caFeatures.forEach(function(f) {
		$("#CAFeatureList").append('<li class="checkbox"><label><input type="checkbox" id="CABox_'+f+'"> '+f+'</label></li>');
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
			$("#CABox_"+f).prop("checked", false);
		});
	});

	$("#buttonClearModels").click(function() {
		$("#CAModelStats").empty();
		caUniqueModelNames.forEach(function(s) {
			caPlot.removeDataSet(s);
		});
		caUniqueModelNames = [];
	});

	$("#buttonAddModel").click(function() {
		toggleAddModelButton(true);
		
		var modelFeatures = [];
		caFeatures.forEach(function(f) {
			if($("#CABox_"+f).is(":checked")) {
				modelFeatures.push(f);
			}
		});
		if(modelFeatures.length == 0) {
			toggleAddModelButton(false);
			return;
		}

		var modelSeed = parseInt($("#inputCASeed").val());

		loadAndDisplayModel(modelFeatures, modelSeed);
	});
}
