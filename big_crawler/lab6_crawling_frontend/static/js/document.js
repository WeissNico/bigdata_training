// javascript functionality specific to document.html
// Author: Johannes Mueller <j.mueller@reply.de>

function showKeywordModal(event) {
    // called, when the keywordModal is shown, saves the cloudId and
    // fills the list with the correct content.
    // `event` refers to the original calling event (show.bs.modal)
    var $button = $(event.relatedTarget);
    var cloudId = $button.data("cloud");
    $(this).find("#wordcloudId").val(cloudId);
    $(this).find("#keywordModalLabel > span").html(cloudId.slice(1));
    var $list = $(this).find(".editable-list ul.list-group");
    fillList($list[0], listFromWordcloud(cloudId));
}

function removeFromWordcloud(event, args) {
    // removes the given word from the wordcloud.
    // `event` refers to the triggering event, 
    // `args` an object holding the keys `list` and `item`.
    var $cloud = $($("#wordcloudId").val());
    var $cloudItem = $cloud.find(`span[data-val='${args.item}']`);
    $cloudItem.remove();
    event.preventDefault();
}

function addToWordcloud(event, args) {
    // removes the given word from the wordcloud.
    // `event` refers to the triggering event,
    // `args` an object holding the keys `list` and `item`.
    var $cloud = $($("#wordcloudId").val());
    var $cloudContainer = $cloud.find("div.cloud-container");
    var $proto = $cloudContainer.find("span.proto");
    var $newItem = $proto.clone().removeClass("proto");
    $newItem.html(args.item);
    $newItem.attr("data-val", args.item);
    $cloudContainer.append($newItem);
    event.preventDefault();
}

function listFromWordcloud(cloudId) {
    // returns a list of words that are currently saved in the wordcloud.
    // `cloudId` the id of the wordcloud.
    var array = $(cloudId).find("span.word").map(function(ind, el) {
        var data = $(el).data("val");
        if (ind === 0 && data === "proto") {
            return;
        }
        return data;
    }).get();
    return array;
}

function saveSettings(event) {
    // saves the settings to the server and reloads the page
    // `event` the original event that triggered the function.
    var $button = $(event.currentTarget);
    var $icon = $button.find(".fas");
    var inputs = $(".document-table input").serializeArray();
    inputs.push({name: "keywords", value: listFromWordcloud("#keywords")});
    inputs.push({name: "entities", value: listFromWordcloud("#entities")});
    
    $icon.addClass("fa-spin");
    jsonPost($button.prop("href"), inputs, function(response) {
        $icon.removeClass("fa-spin");
        if (!response.success) {
            $button.removeClass("btn-primary").addClass("btn-danger");
        }
        else {
            $button.removeClass("btn-primary").addClass("btn-success");
        }
    });
    event.preventDefault();
}

function focusInput(event) {
    var $modal = $(event.currentTarget)
    $modal.find(".editable-list input[name='newItem']").focus();
}

$(GLOBAL_OBJ).on("custom.edit-list.remove", removeFromWordcloud);
$(GLOBAL_OBJ).on("custom.edit-list.add", addToWordcloud);
$("#keywordModal").on("show.bs.modal", showKeywordModal);
$("#keywordModal").on("shown.bs.modal", focusInput);
$("#saveButton").on("click", saveSettings);