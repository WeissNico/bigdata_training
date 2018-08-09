// Add options to the lists of the searchdialog

function add_option(link_id) {
    return function(_event) {
        var url = "/_" + link_id;
        var form_id = "#" + link_id + "_form";
        var list_id = "#" + link_
        var $form = $(form_id)
        var $list = $(list_id)
        $.ajax({
            type: 'POST',
            url: "/_" + link_id,
            data: {$form},
            success: function(response) {
                console.log(response);
            }
        });
    };
};

$("#add_source_button").click(add_option("add_source"));
$("#add_period_button").click(add_option("add_period"));