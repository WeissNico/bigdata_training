// Adds custom functionality to the dashboard.html site.
// Author: Johannes Mueller <j.mueller@reply.de>

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
    $button.children(".button-text").html(mapping.text);
    // show or hide the spinner
    $button.children(".fas").toggle($button.data("val") === "");
}

function changeButton(event) {
    // changes the color and label of a button, when the according action is chosen
    // `event` refers to the original input event.
    var $link = $(event.target);
    var $button = $link.parent(".dropdown-status").prev(".btn");
    // set data-value to nothing, which should show the loading spinner
    $button.data("val", "");
    $button.trigger("custom.change.val")
    // reset in the success function
    jsonPost($link.prop("href"), [{name: "status", value: $link.data("val")}],
        function (response) {
            if (response.success) {
                $button.data("val", response.update.status);
                $button.trigger("custom.change.val")
                updateBadges();
            }
        });
    event.preventDefault();
}

function changeImpactIndicator(event) {
    // changes the impact indicator to it data-val attribute.
    // `event` references the original event.
    var $indicator = $(event.target);
    var value = $indicator.data("val");
    $indicator.removeClass("high medium low");
    $indicator.addClass(value);
    var $spans = $indicator.find("span");
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

    jsonPost($link.prop("href").replace("%25", docId), formData,
        function (response) {
            if (response.success) {
                for (key in response.update) {
                    $tr.find(`[data-var='${key}']`).data("val", response.update[key]);
                    $tr.find(`[data-var='${key}']`).trigger("custom.change.val");
                }
            }
        });
    event.preventDefault();
    $modal.modal("hide");
}


$(".btn-status").on("custom.change.val", changeStatusButtonColor);
$(".table-entry").on("custom.change.val", changeTableEntry);
$(".impact-indicator").on("custom.change.val", changeImpactIndicator);

$(".dashboard-header").click(flipIcon.bind(["fa-caret-right",
                                            "fa-caret-down"]));
$(".dashboard .dropdown-item-status").click(changeButton);

$("#changeModal").on("show.bs.modal", showChangeModal);
$("#changeDocumentPropertiesButton").click(changeProperties);

$(".dashboard .btn-status").trigger("custom.change.val");