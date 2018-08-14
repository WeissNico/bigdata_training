/* Javascript functionality for the connections page. */

function triggerPDFPreview(event) {
    // updates the pdf-preview sidepane, when an event is fired.
    // `event` refers to the original event.
    var $tr = $(event.target).parents("tr");
    var docId = $tr.data("document");
    $(".pdf-container").trigger("custom.change.pdf", docId);
}

function changePDF(event, docId) {
    // triggered upon a 'custom.change.pdf' event, replaces the document as
    // defined by the `docId`, given in the first event argument.
    // assume 'object', change on 'iframe'
    var baseUrl = $(this).data("base-url");
    $(this).prop("data", baseUrl.replace("0", docId));
    $(this).children("a").prop("href", baseUrl.replace("0", docId));
}

$(".pdf-container").on("custom.change.pdf", changePDF);
$("tr").click(triggerPDFPreview);