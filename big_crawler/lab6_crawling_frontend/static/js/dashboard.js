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

function accumulateJobs(event) {
    // accumulates all the open jobs of a month and updates the display-badges.
    // `event` describes the originally triggered event, its target describes
    //      the month, which the jobs should be accumulated for.
    var $monthDiv = $(event.target);
    var $monthLink = $monthDiv.prev(".nav-item");
    var sums = {"open": 0, "waiting": 0, "finished": 0};
    $monthDiv.children(".nav-item").each(function() {
        $(this).find(".badge.indicator").children(".data-span")
         .each(function() {
            sums[$(this).data("var")] += parseInt($(this).text())
        });
    });
    $monthLink.find(".data-span").each(function() {
        $(this).html(sums[$(this).data("var")]);
    });
    $monthLink.find(".badge.indicator").trigger("custom.change.badges");
}

function changeIndicatorColors(event) {
    // changes the color of the given indicator.
    // `element` refers to an indicator badge (.badge.indicator)
    var $badge = $(event.target);
    var $dataSpans = $badge.find(".data-span");
    var classes = Object.values(STATUS_MAPPING).map(el => `badge-${el.color}`)
                                               .join(" ");
    var values = $dataSpans.map(function(_, el) {
        return {
            type: $(el).data("var"),
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
        return $(this).data("val");
    }).get();
    var freqs = numbers.reduce(function (acc, val) {
        acc[val] = acc[val] + 1;
        return acc;
    },
    {open: 0, waiting: 0, finished: 0});
    // update header
    var $headerBadges = $("h1 .badge");
    $headerBadges.each(function() {
        $(this).html(freqs[$(this).data("var")]);
    });
    // update dashboard overview badges
    var $sidepanelBadge = $(".nav-link.active").prev(".badge.indicator");
    var $sidepanelSpans  = $sidepanelBadge.find(".data-span");
    $sidepanelSpans.each(function() {
        $(this).html(freqs[$(this).data("var")]);
    });
    $sidepanelBadge.trigger("custom.change.badges");
    // update months badges
    var $monthDiv = $(".cat-link.active").parent("li").next("div");
    $monthDiv.trigger("custom.change.badges");
}

function toTitleCase(str) {
    // converts a given string or sentence to titlecase.
    // `str` depicts the given word or sentence
    words = str.split(" ");
    for (var i=0; i < words.length; ++i) {
        words[i] = words[i].charAt(0).toUpperCase() + words[i].substring(1);
    }
    return words.join(" ");
}

function changeStatusButtonColor(event) {
    // sets the color of the status toggle accordingly.
    // `element` corresponds to the button this should be done for
    var $button = $(event.target);
    var classes = Object.values(STATUS_MAPPING).map(el => `btn-${el.color}`).join(" ");
    var mapping = STATUS_MAPPING[$button.data("val")]
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
                $button.data("val", response.status);
                $button.trigger("custom.change.val")
                updateBadges();
            }
        }
    });
    event.preventDefault();
}

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

function changeImpactIndicator(event) {
    // changes the impact indicator to it data-val attribute.
    // `event` references the original event.
    var $indicator = $(event.target);
    var value = $indicator.data("val");
    $indicator.removeClass("high medium low");
    $indicator.addClass(value);
    $spans = $indicator.children("span");
    $spans.first().text(value.charAt(0).toUpperCase());
    $spans.last().text(toTitleCase(value));
}

function changeTableEntry(event) {
    // changes the table entry to its data-val attribute.
    // `event` references the original event.
    var $tableEntry = $(event.target);
    $tableEntry.text($tableEntry.data("val"));
}

function showChangeModal(event) {
    // fills in the correct values into the modal dialog
    // `event` the orignal click event.
    var $button = $(event.relatedTarget);
    var docId = $button.data("document");
    var $modal = $(this);

    var $tr = $button.parents("tr");
    var $titleLink = $tr.find("[data-var='title']");
    var impact = $tr.find("[data-var='impact']").data("val");
    var type = $tr.find("[data-var='type']").text();
    var category = $tr.find("[data-var='category']").text();

    $modal.find("#documentId").val(docId);

    var impactVal = $modal.find("#impactValue");
    impactVal.val(impact);
    $(impactVal.data("display")).html(toTitleCase(impact));

    $modal.find("#typeValue").val(type);
    $modal.find("#categoryValue").val(category);
    $modal.find("#documentTitleLink").empty();
    $modal.find("#documentTitleLink").append($titleLink.clone());
}

function changeProperties(event) {
    // changes the documents properties using an ajax call.
    // `event` refers to the original click event.
    var $link  = $(event.target);
    var $modal = $link.parents(".modal");
    var $form = $modal.find("#changeDocumentPropertiesForm");
    var formData = $form.serializeArray();
    var docId = $form.find("#documentId").val();
    var $tr = $(`tr[data-document='${docId}'`);

    $.ajax({
        type: "GET",
        url: $link.prop("href"),
        data: formData,
        success: function(response) {
            if (response.success) {
                for (key in response.update) {
                    $tr.find(`[data-var=${key}]`).data("val", response.update[key]);
                    $tr.find(`[data-var=${key}]`).trigger("custom.change.val");
                }
            }
        }
    });
    event.preventDefault();
    $modal.modal("hide");
}


$(".btn-status").on("custom.change.val", changeStatusButtonColor);
$(".table-entry").on("custom.change.val", changeTableEntry);
$(".impact-indicator").on("custom.change.val", changeImpactIndicator);
$(".badge.indicator").on("custom.change.badges", changeIndicatorColors);
$(".category").on("custom.change.badges", accumulateJobs);

$(".cat-link").click(changeCaret);
$(".dashboard-header").click(changeCaret);
$(".dashboard .dropdown-item-status").click(changeButton);

$(".fakeSelect .dropdown-item").click(changeInputElement);
$("#changeModal").on("show.bs.modal", showChangeModal);
$("#changeDocumentPropertiesButton").click(changeProperties);

$(".dashboard .btn-status").trigger("custom.change.val");
$(".badge.indicator").trigger("custom.change.badges");
$(".category").trigger("custom.change.badges");