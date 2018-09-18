/* Script kept old search functionallity regarding tags, but also added
   new functions for filtered_search.html
   Author: Johannes Mueller <j.mueller@reply.de>
*/
function deleteTag(e) {
    var doc_id = e.target.parentElement.parentElement.getAttribute('data-value')
    e.target.remove()

    $.ajax({
        type: 'POST',
        url: "/removeTag",
        data: {doc_id: doc_id, tag: e.target.innerText},
        success: function(response) {
            console.log(response);
        }
    });
}

function addTag(e){
    if(e.key === 'Enter') {
        var btn = document.createElement("button");
        btn.addEventListener('dblclick', deleteTag);
        btn.className = "btn btn-outline-success my-2 my-sm-0"
        btn.type="submit"
        btn.innerHTML = e.target.value;
        var wrapper = e.target.parentElement
        wrapper.appendChild(btn);
        doc_id = e.target.parentElement.parentElement.getAttribute('data-value')

        $.ajax({
          type: 'POST',
          url: "/addTag",
          data: {doc_id: doc_id, tag: e.target.value},
          success: function(response) {
                console.log(response);
            }
        });
    }
}

function updateOutputs(event) {
    // updates the outputs for the range sliders.
    // `event` refers to the original input event on the slider.
    var $input = $(event.target);
    var $output = $(`output[for=${$input.attr("id")}]`);
    $output.text(parseFloat($input.val()).toFixed(1));
}

function invalidateInputs(event) {
    // invalidates all inputs except for q, such that only q is submitted
    // `event` refers to the button click event.
    var $form = $(event.currentTarget.form);
    $form.find("input:not([name=q])").attr("disabled", "disabled");
}

// set a listener for the range sliders
$(document).on("input", "input[type='range']", updateOutputs);
// and trigger it once
$("input[type='range']").trigger("input");
// before triggering the search button invalidate all other inputs
$("#searchButton").click(invalidateInputs);