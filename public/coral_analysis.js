
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
    var margin = 50;
    var height2Width = 0.45;
	return [window.innerWidth-margin, Math.round(height2Width*(window.innerWidth-margin))];
}

function initCAGUI() {
    caFeatures.forEach(function(f) {
        $("#CAFeatureList").append('<li class="checkbox"><label id="CALabel_'+f+'"><input type="checkbox" id="CABox_'+f+'"> '+f+'</label></li>');
        //$("#CABox_"+f).change(function() {
        //    if($(this).is(":checked")) {
        //        $("#CALabel_"+f).css("background", "red");
        //    }
        //    else {
        //        $("#CALabel_"+f).css("background", "white");
        //    }
        //});
    });
    

    caPlot = new CanvasTimeSeriesPlot(d3.select("#CAPlot"), getCAPlotSize(), {
        yAxisLabel: "p_Extension",
        markerLineWidth: 3,
        markerRadius: 5
    });
    caPlot.setZoomYAxis(false);
    caPlot.addDataSet("observations", "Observations", caObservations, "steelblue", true);
    caPlot.updateDomains(caPlot.calculateXDomain(), [-0.1, 1.1], false);

    $(window).resize(function() {
		caPlot.resize(getCAPlotSize());
	});
}


