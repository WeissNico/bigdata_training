$(".custom-check-list > li").each(function(_ind) {
    // for each checkbox in a li element add a listener to the change of
    // the checkbox and connect it to the presence of the active-class
    var $parent = $(this);
    var $checkbox = $(this).children("input[type='checkbox']");
    var $mark = $(this).children(".fas");

    // add a click listener to change the checkbox behaviour
    $parent.click(function(_event) {
        var state = !$checkbox.prop("checked")
        // set checkbox
        $checkbox.prop("checked", state);
        if (state) {
            $parent.addClass("active");
        }
        else {
            $parent.removeClass("active");
        }
        // show checkmark
        $mark.css("visibility", state ? "visible" : "hidden");
        _event.preventDefault();
    });
});