// This script handles the file-upload to the server, the drag-and-drop input
// and the updates of the progress bars.

function noDefault(event) {
    // just stop the default action of the element.
    // `event` refers to the original event.
    event.stopPropagation();
    event.preventDefault();
}

function setUploadFormActive(event) {
    // adds the active class while dragging files over the element.
    // `event` refers to the original dragenter-event.
    noDefault(event);
    var $uploadForm = $(".drop-area");
    $uploadForm.addClass("active")
}

function setUploadFormInactive(event) {
    // adds the active class while dragging files over the element.
    // `event` refers to the original dragenter-event.
    noDefault(event);
    var $uploadForm = $(".drop-area");
    $uploadForm.removeClass("active")
}

function addFileList(fileList) {
    // adds the items contained in the given fileList, to the uploadForms
    // own `data-files` attribute.
    // Filters out filetypes that are not of type pdf.
    // `fileList` a FileList, either from imput or dataTransfer.
    var $uploadForm = $("#uploadForm");
    var files = $uploadForm.data("files");
    if (files === undefined) {
        files = [];
    }

    for (let file of fileList) {
        if (file.type !== "application/pdf") {
            continue;
        }
        files.push(file);
    }
    $uploadForm.data("files", files);
    $uploadForm.trigger("custom.change.files");
}

function dropFiles(event) {
    // handle the dropping of files into the drop area.
    // `event` refers to the original drop-event.
    setUploadFormInactive(event);

    var dataTransfer = event.originalEvent.dataTransfer;
    addFileList(dataTransfer.files);
}

function changeFileInput(event) {
    // gets called when new files are selected via the file input
    // `event` refers to the original change event.
    var input = event.currentTarget;
    addFileList(input.files);
}

function displayFiles() {
    // display the files as progress bars in the list.

    var $uploadForm = $("#uploadForm");
    // first put the files into the input event:
    var $fileInput = $("#fileInput");
    $fileInput.files = $uploadForm.data("files");

    var $list = $("ul.file-progress");
    var $proto = $list.find("li.proto");
    // clear list before readding the files.
    $list.empty();
    // add the prototype again.
    $list.append($proto);
    var files = $uploadForm.data("files");
    files.forEach(function(file, idx) {
        var $item = $proto.clone().removeClass("proto");
        $item.data("key", idx);
        $item.find(".filename").html(file.name);
        // add the delete listener
        $item.find(".remove-file").on("click", removeFile);
        $list.append($item);
    });
}

function removeFile(event) {
    // removes a file from the list.
    // `event` refers to the original click-event.
    noDefault(event);
    var $uploadForm = $("#uploadForm");
    var $item = $(event.currentTarget).parents("li.file-progress-item");
    var files = $uploadForm.data("files");
    files.splice($item.data("key"), 1);
    $uploadForm.trigger("custom.change.files");
}

function uploadProgress(event) {
    // update the progress bars using the given progress-event.
    // `this` should contain the `key` of the file.
    // `event` refers to the original progress-event.
    var percent = `${parseInt(event.loaded / event.total * 100)}%`;
    // pick the key+1th item of the list (+1 because of the prototype)
    var $item = $($("li.file-progress-item")[this.key + 1]);
    var $progressBar = $item.find(".progress-bar");
    $progressBar.css({width: percent});
    $progressBar.html(percent);
}

function uploadSuccess(response) {
    // handle the success.
    // `this` should contain the `key` of the file.
    var $item = $($("li.file-progress-item")[this.key + 1]);
    var $progressBar = $item.find(".progress-bar");
    $progressBar.removeClass("progress-bar-animated");
    if (response.success){
        // change check
        $item.find(".fas").removeClass("fa-trash")
            .addClass("fa-check text-success");
    }
    else {
        // change cross
        $item.find(".fas").removeClass("fa-trash")
             .addClass("fa-times text-danger")
             .prop("title", response.message);
    }
    $item.find(".filename").prop("href", response.href);
}

function uploadFiles(event) {
    // upload the files,
    // `event` refers to the original submit event.
    noDefault(event);
    var form = document.forms.namedItem("fileUploadForm");
    var $uploadForm = $("#uploadForm");
    var files = $uploadForm.data("files");
    // invalidate delete buttons
    $(".remove-file").off("click");

    files.forEach(function(file, index) {
        // uploads the files to the server
        let formData = new FormData();
        formData.append("__ajax", "true");
        formData.append("file_input", file);
        $.ajax({
            url: form.action,
            type: form.method,

            data: formData,

            cache: false,
            contentType: false,
            processData: false,

            xhr: function() {
                var req = $.ajaxSettings.xhr();
                if (req.upload) {
                    // For handling the progress of the upload
                    // `bind` the index as `this` such that the right
                    // progressbars can be updated
                    req.upload.addEventListener('progress',
                                                uploadProgress.bind({
                                                    key: index
                                                }),
                                                false);
                }
                return req;
            },

            success: uploadSuccess.bind({key: index})
        });
    });

}

// listen to the change event on the input.
$(".upload-form").on("custom.change.files", displayFiles);
$(document).on("submit", "#fileUploadForm", uploadFiles);
$(document).on("change", "#fileInput", changeFileInput);
$(document).on("dragenter", ".drop-area", setUploadFormActive);
$(document).on("dragover", ".drop-area", setUploadFormActive);
$(document).on("dragleave", ".drop-area", setUploadFormInactive);
$(document).on("dragend", ".drop-area", setUploadFormInactive);
$(document).on("drop", ".drop-area", dropFiles);
// prevent default, such that no mistakes happen.
$(document).on("drop", noDefault);