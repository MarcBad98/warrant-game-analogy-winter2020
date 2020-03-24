$(document).ready(function() {

    // -------------------------------------------------------------------------------------------------------------- //
    // CONDITIONALLY VISIBLE & REQUIRED FORM FIELDS                                                                   //
    // -------------------------------------------------------------------------------------------------------------- //

    var slide_speed = 750;

    function ConditionalMoveChoice() {

        // show the move form only if an option is selected
        if ($("input[type=radio][name='move_choice']:checked").length > 0) $("#idle").fadeIn(slide_speed); else $("#idle").fadeOut(slide_speed);

        // show/hide the attack form
        if ($("input[type=radio][name='move_choice'][value='attack']:checked").val()) {
            $("#attack").slideDown(slide_speed);
            $("input[type=radio][name='link']:checked").attr('required', "");
            $("#id_explain_attack").attr('required', "");
        } else {
            $("#attack").slideUp(slide_speed);
            $("input[type=radio][name='link']:checked").removeAttr('required');
            $("#id_explain_attack").val(""); $("#id_explain_attack").removeAttr('required');
        }

        // show/hide the update rule form
        if ($("input[type=radio][name='move_choice'][value='update_rule']:checked").val()) {
            $("#update-rule").slideDown(slide_speed);
            $("#id_update_antecedent").attr('required', "");
            $("#id_update_consequent").attr('required', "");
        } else {
            $("#update-rule").slideUp(slide_speed);
            $("#id_update_antecedent").val(""); $("#id_update_antecedent").removeAttr('required');
            $("#id_update_consequent").val(""); $("#id_update_consequent").removeAttr('required');
        }

        // show/hide the update facts form
        if ($("input[type=radio][name='move_choice'][value='update']:checked").val()) {
            $("#update-facts").slideDown(slide_speed);
            $("#id_edit").attr('required', "");
            $("#id_source_replace").attr('required', "");
            $("#id_target_replace").attr('required', "");
        } else {
            $("#update-facts").slideUp(slide_speed);
            $("#id_edit").val(""); $("#id_edit").removeAttr('required');
            $("#id_source_replace").val(""); $("#id_source_replace").removeAttr('required');
            $("#id_target_replace").val(""); $("#id_target_replace").removeAttr('required');
        }

        // show/hide the add facts form
        if ($("input[type=radio][name='move_choice'][value='add']:checked").val()) {
            $("#add-facts").slideDown(slide_speed);
            $("#id_source_add").attr('required', "");
            $("#id_target_add").attr('required', "");
            $("#id_explain_add").attr('required', "");
        } else {
            $("#add-facts").slideUp(slide_speed);
            $("#id_source_add").val(""); $("#id_source_add").removeAttr('required');
            $("#id_target_add").val(""); $("#id_target_add").removeAttr('required');
            $("#id_explain_add").val(""); $("#id_explain_add").removeAttr('required');
        }

        // show/hide the report form
        if ($("input[type=radio][name='move_choice'][value='report']:checked").val()) {
            $("#report").slideDown(slide_speed);
            $("#id_text").attr('required', "");
        } else {
            $("#report").slideUp(slide_speed);
            $("#id_text").val(""); $("#id_text").removeAttr('required');
        }

        // show/hide the pass form
        if ($("input[type=radio][name='move_choice'][value='pass']:checked").val()) $("#pass").slideDown(slide_speed); else $("#pass").slideUp(slide_speed);

    }
    ConditionalMoveChoice();
    $("input[type=radio][name='move_choice']").change(ConditionalMoveChoice);


    function ConditionalLinkChoice() {

        if ($("input[type=radio][name='link']:checked").val()) {
            if ($("input[type=radio][name='link'][value='L1']:checked").val()) $("#1-instructions").slideDown(slide_speed); else $("#1-instructions").slideUp(slide_speed);
            if ($("input[type=radio][name='link'][value='L2']:checked").val()) $("#2-instructions").slideDown(slide_speed); else $("#2-instructions").slideUp(slide_speed);
            if ($("input[type=radio][name='link'][value='L3']:checked").val()) $("#3-instructions").slideDown(slide_speed); else $("#3-instructions").slideUp(slide_speed);
            if ($("input[type=radio][name='link'][value='L4']:checked").val()) $("#4-instructions").slideDown(slide_speed); else $("#4-instructions").slideUp(slide_speed);
            if ($("input[type=radio][name='link'][value='L5']:checked").val()) $("#5-instructions").slideDown(slide_speed); else $("#5-instructions").slideUp(slide_speed);
            $("#explain-attack").slideDown(slide_speed);
        } else {
            $("#explain-attack").slideUp(slide_speed);
            $("#id_explain_attack").val('');
            $("#1-instructions").slideUp(slide_speed);
            $("#2-instructions").slideUp(slide_speed);
            $("#3-instructions").slideUp(slide_speed);
            $("#4-instructions").slideUp(slide_speed);
            $("#5-instructions").slideUp(slide_speed);
        }

    }
    ConditionalLinkChoice();
    $("input[type=radio][name='link']").change(ConditionalLinkChoice);


    function ConditionalAttackResponse() {

        if ($("input[type=radio][name='response'][value='reject']:checked").val()) {
            $("#reject-attack").slideDown(slide_speed);
            $("#id_explain").attr('required', "");
        } else {
            $("#reject-attack").slideUp(slide_speed);
            $("#id_explain").val(""); $("#id_explain").removeAttr('required');
        }

    }
    ConditionalAttackResponse();
    $("input[type=radio][name='response']").change(ConditionalAttackResponse);


    function ConditionalEditResponse() {

        if ($("input[type=radio][name='response'][value='reject']:checked").val()) {
            $("#alternative-edit-proposal").slideUp(slide_speed);
            $("#reject-edit-proposal").slideDown(slide_speed);
            $("#id_explain_reject").attr('required', "");
            $("#id_source_replace").val(""); $("#id_source_replace").removeAttr('required');
            $("#id_target_replace").val(""); $("#id_target_replace").removeAttr('required');
        } else if ($("input[type=radio][name='response'][value='modify']:checked").val()) {
            $("#alternative-edit-proposal").slideDown(slide_speed);
            $("#reject-edit-proposal").slideDown(slide_speed);
            $("#id_explain_reject").attr('required', "");
            $("#id_source_replace").attr('required', "");
            $("#id_target_replace").attr('required', "");
        } else {
            $("#reject-edit-proposal").slideUp(slide_speed);
            $("#alternative-edit-proposal").slideUp(slide_speed);
            $("#id_explain_reject").val(""); $("#id_explain_reject").removeAttr('required');
            $("#id_source_replace").val(""); $("#id_source_replace").removeAttr('required');
            $("#id_target_replace").val(""); $("#id_target_replace").removeAttr('required');
        }

    }
    ConditionalEditResponse();
    $("input[type=radio][name='response']").change(ConditionalEditResponse);


    function ConditionalAddResponse() {

        if ($("input[type=radio][name='response'][value='reject']:checked").val()) {
            $("#alternative-add-proposal").slideUp(slide_speed);
            $("#reject-add-proposal").slideDown(slide_speed);
            $("#id_explain_reject").attr('required', "");
            $("#id_source_add").val(""); $("#id_source_add").removeAttr('required');
            $("#id_target_add").val(""); $("#id_target_add").removeAttr('required');
        } else if ($("input[type=radio][name='response'][value='modify']:checked").val()) {
            $("#alternative-add-proposal").slideDown(slide_speed);
            $("#reject-add-proposal").slideDown(slide_speed);
            $("#id_explain_reject").attr('required', "");
            $("#id_source_add").attr('required', "");
            $("#id_target_add").attr('required', "");
        } else {
            $("#reject-add-proposal").slideUp(slide_speed);
            $("#alternative-add-proposal").slideUp(slide_speed);
            $("#id_explain_reject").val(""); $("#id_explain_reject").removeAttr('required');
            $("#id_source_add").val(""); $("#id_source_add").removeAttr('required');
            $("#id_target_add").val(""); $("#id_target_add").removeAttr('required');
        }

    }
    ConditionalAddResponse();
    $("input[type=radio][name='response']").change(ConditionalAddResponse);

});
