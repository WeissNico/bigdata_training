// Adds custom functionality to the dashboard.html site.
// Author: Johannes Mueller <j.mueller@reply.de>
var STATUS_MAPPING = {"open": {text: "UNREAD", color: "danger", rank: 0},
                      "waiting": {text: "ON HOLD", color: "warning", rank: 1},
                      "finished": {text: "ASSIGNED", color: "success", rank: 2}
                     };

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
        $(this).find(".badge.indicator").children(".data-span")
         .each(function() {
            sums[$(this).attr("data-var")] += parseInt($(this).text())
        });
    });
    $monthLink.find(".data-span").each(function() {
        $(this).html(sums[$(this).attr("data-var")]);
    });
    $monthLink.find(".badge.indicator").each(changeIndicatorColors);
}

function changeIndicatorColors(_, element) {
    // changes the color of the given indicator.
    // `element` refers to an indicator badge (.badge.indicator)
    var $badge = $(element);
    var $dataSpans = $badge.find(".data-span");
    var classes = Object.values(STATUS_MAPPING).map(el => `badge-${el.color}`)
                                               .join(" ");
    var values = $dataSpans.map(function(_, el) {
        return {
            type: $(el).attr("data-var"),
            number: $(el).text()
        };
    }).get();
    var mode = values.reduce(function(acc, val) {
        // continue, when there are 0 occurences
        if (val.number == 0) return acc;
        if (STATUS_MAPPING[val.type].rank < STATUS_MAPPING[acc].rank) {
            acc = val.type;
        }
        return acc;
    }, "finished");
    var mapping = STATUS_MAPPING[mode];
    $badge.removeClass(classes).addClass(`badge-${mapping.color}`);
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
    var $sidepanelBadge = $(".nav-link.active").prev(".badge.indicator");
    var $sidepanelSpans  = $sidepanelBadge.find(".data-span");
    $sidepanelSpans.each(function() {
        $(this).html(freqs[$(this).attr("data-var")]);
    });
    changeIndicatorColors(0, $sidepanelBadge);
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
$(".badge.indicator").each(changeIndicatorColors);
$(".dashboard-header").click(changeCaret);
$(".category").each(accumulateJobs);
$(".dashboard .btn-status").each(setButtonColor);
$(".dashboard .dropdown-item-status").click(changeButton);