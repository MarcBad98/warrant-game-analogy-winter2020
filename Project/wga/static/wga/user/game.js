$(document).ready(function() {

    //----------------------------------------------------------------------------------------------------------------//
    // WEB SOCKETS                                                                                                    //
    //----------------------------------------------------------------------------------------------------------------//

    var socket = new ReconnectingWebSocket('ws://' + window.location.host + '/ws' + window.location.pathname);

    socket.onmessage = function(e) {
        var data = JSON.parse(e.data);
        if (data.hasOwnProperty('html-interface'))          UpdateInterface(data);
        else if (data.hasOwnProperty('message'))            UpdateMessages(data);
    };

    function AddSubmitListener() {
        $("#move-form").submit(function(e) {
            e.preventDefault();
            socket.send(JSON.stringify($("#move-form").serializeObject()));
        });
    }
    AddSubmitListener();

    function UpdateInterface(data) {
        $("#game-interface").html(data['html-interface']);
        AddSubmitListener();
    }

    function UpdateMessages(data) {
        $("#message-list").append("<li class=\"message\">" + data['message'] + "</li>");
    }

    function RecordTime() { var d = new Date(); return d.getTime(); }
    var start = RecordTime();
    $(window).focus(function()  { start = RecordTime(); });
    $(window).blur(function()   { var final = RecordTime(); socket.send(JSON.stringify({'time': (final - start) / 1000})); });

});
