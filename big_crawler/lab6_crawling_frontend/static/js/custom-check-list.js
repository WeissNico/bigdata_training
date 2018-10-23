function toggleActive(event) {
    // Toggles the active class of the li item, which is the parent of the
    // checkbox.
    // `event` refers to the original click event.
    var $checkbox = $(event.currentTarget);
    var $parent = $checkbox.parents("li");

    var state = $checkbox.prop("checked");
    if (state) {
        $parent.addClass("active");
    }
    else {
        $parent.removeClass("active");
    }
    // show checkmark
    $parent.find(".fa-check").css("visibility", state ? "visible" : "hidden");
}

$(".custom-check-list input[type='checkbox']").on("change", toggleActive);