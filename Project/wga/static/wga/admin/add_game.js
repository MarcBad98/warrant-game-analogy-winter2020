$(document).ready(function() {

    //----------------------------------------------------------------------------------------------------------------//
    // SEND WARNINGS                                                                                                  //
    //----------------------------------------------------------------------------------------------------------------//

    function SendWarnings() {
        $.post("./check", $("#admin-form").serialize(), function(data) {
            if (data['adv'] && data['crt']) $("#warnings").html("<div class=\"alert alert-warning\"> Both Advocate and Critic have already played the scenario.</div>");
            else if (data['adv'])           $("#warnings").html("<div class=\"alert alert-warning\"> Advocate has already played the scenario.</div>");
            else if (data['crt'])           $("#warnings").html("<div class=\"alert alert-warning\"> Critic has already played the scenario.</div>");
            else                            $("#warnings").html("");
        });
    }

    $("#id_scenario").change(SendWarnings);
    $("#id_advocate").change(SendWarnings);
    $("#id_critic").change(SendWarnings);

    //----------------------------------------------------------------------------------------------------------------//
    // AJAX CSRF TOKEN SETUP                                                                                          //
    //----------------------------------------------------------------------------------------------------------------//

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var csrftoken = getCookie('csrftoken');
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

});
