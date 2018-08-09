// Adds custom functionality to the dashboard.html site.
// Author: Johannes Mueller <j.mueller@reply.de>
var STATUS_MAPPING = {"open": {text: "UNREAD", color: "danger"},
                      "waiting": {text: "ON HOLD", color: "warning"},
                      "finished": {text: "ASSIGNED", color: "success"}}

function changeCaret(event){
    // changes the caret of the cat-links according to the expansion of the
    // referenced div.
    // `event` describes the input-event
    var $catLink = $(event.target);
    var $collapse = $($catLink.prop("hash"));
    var $caret = $catLink.children(".fas");
    var toggled = $collapse.hasClass("show");
    $caret.toggleClass("fa-caret-down", !toggled);
    $caret.toggleClass("fa-caret-right", toggled);
}

function accumulateJobs(_, element) {
    // accumulates all the open jobs of a month and updates the display-badges.
    // `element` describes the month, which the jobs should be accumulated for.
    var $monthDiv = $(element);
    var $monthLink = $monthDiv.prev(".nav-item");
    var sums = {"open": 0, "waiting": 0, "finished": 0};
    $monthDiv.children(".nav-item").each(function() {
        $(this).find(".badges .badge").each(function() {
            sums[$(this).attr("data-var")] += parseInt($(this).text())
        });
    });
    $monthLink.find(".badges .badge").each(function() {
        $(this).html(sums[$(this).attr("data-var")]);
    });
}

function updateBadges() {
    // updates all the related badges, should be triggered, when the button
    // is changed.
    var numbers = $(".btn-status").map(function() {
        return $(this).attr("data-val");
    }).get();
    var freqs = numbers.reduce(function (acc, val) {
        acc[val] = acc[val] + 1;
        return acc;
    },
    {open: 0, waiting: 0, finished: 0});
    // update header
    var $headerBadges = $("h1 .badge");
    $headerBadges.each(function() {
        $(this).html(freqs[$(this).attr("data-var")]);
    });
    // update dashboard overview badges
    var $sidepanelBadges = $(".nav-link.active").prev().children(".badge");
    $sidepanelBadges.each(function() {
        $(this).html(freqs[$(this).attr("data-var")]);
    });
    // update months badges
    var $monthDiv = $(".cat-link.active").parent("li").next("div");
    accumulateJobs(0, $monthDiv);
}

function setButtonColor(_, element) {
    // sets the color of the status toggle accordingly.
    // `element` corresponds to the button this should be done for
    var $button = $(element);
    var classes = Object.values(STATUS_MAPPING).map(el => `btn-${el.color}`).join(" ");
    var mapping = STATUS_MAPPING[$button.attr("data-val")]
    $button.removeClass(classes).addClass(`btn-${mapping.color}`);
    $button.html(mapping.text);
}

function changeButton(event) {
    // changes the color and label of a button, when the according action is chosen
    // `event` refers to the original input event.
    var $link = $(event.target);
    var $button = $link.parent(".dropdown-status").prev(".btn");
    $.ajax({
        type: 'GET',
        url: $link.prop("href"),
        success: function(response) {
            if (response.success) {
                $button.attr("data-val", response.status);
                setButtonColor(0, $button);
                updateBadges();
            }
        }
    });
    event.preventDefault();
}

$(".cat-link").click(changeCaret);
$(".dashboard-header").click(changeCaret);
$(".category").each(accumulateJobs);
$(".dashboard .btn-status").each(setButtonColor);
$(".dashboard .dropdown-item-status").click(changeButton);