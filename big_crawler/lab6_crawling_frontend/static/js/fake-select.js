// This script adds functionallity for the fake-select box.
// Author: Johannes Mueller <j.mueller@reply.de>
function changeInputElement(event) {
    // changes the preceding input element, when clicking on a dropdown-item.
    // `event` references the original click event.
    var $trigger = $(event.target);
    var $input = $trigger.parent(".dropdown-menu").prevAll("input");
    $input.val($trigger.data("val"));
    // if a data-display attribute is set, find the element with this id and
    // set it's html accordingly
    if ($input.data("display")) {
        $($input.data("display")).html($trigger.text());
    }
    event.preventDefault();
}

$(".fakeSelect .dropdown-item").click(changeInputElement);