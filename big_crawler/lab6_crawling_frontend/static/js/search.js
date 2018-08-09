function deleteTag(e) {
    doc_id = e.target.parentElement.parentElement.getAttribute('data-value')
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
