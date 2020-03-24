$(document).ready(function() {

    //----------------------------------------------------------------------------------------------------------------//
    // WEB SOCKETS                                                                                                    //
    //----------------------------------------------------------------------------------------------------------------//

    var socket = new ReconnectingWebSocket('ws://' + window.location.host + '/ws' + '/wganalogy_app/nav');

    socket.onmessage = function(e) {
        var data = JSON.parse(e.data);
        UpdateNavigation(data);
    };

    function UpdateNavigation(data) {
        $("#navbar").html(data['html-navigation']);
    }

});
