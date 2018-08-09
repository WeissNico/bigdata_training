$(document).ready(function () {
    $('body').on('click', '.category_id',function(){
    //document.getElementById("category_id").value = $(this).attr('data');
    $('#category').val($(this).attr('data'));
    $('#category_id').val($(this).attr('data-id'));
    console.log($(this).attr('data'));
    console.log($(this).attr('data-id'));
    });
});

function addSeed(e){

        name = $('#nameFormControlInput')[0].value
        //category = $('#categoryFormControlInput')[0].value
        category = $('#category')[0].value
        url = $('#urlFormControlInput')[0].value
        category_id = category = $('#category_id')[0].value
        doc_id = category_id + '#' + name

        $.ajax({
          type: 'POST',
          url: "/addSeed",
          data: {category: category, category_id:category_id, name: name, url: url},
          success: function(response) {
                console.log(response);
            }
        });

        $('#'+category_id+ ' li:last').after(
            $('<li/>', {'class': 'list-group-item list-group-item-action flex-column align-items-start'}).append(
                $('<div/>', {'class': 'd-flex w-100 justify-content-between'}).append(
                    $('<h5/>', {text: name, 'class':'mb-1'})
                ).append(
                    $('<button/>', {text: 'Delete', 'class': 'btn btn-outline-danger my-2 my-sm-0',  on: { click: deleteSeed}, 'data-value': doc_id})
                )
            )
            .append(
                $('<small/>').append(
                     $('<a/>', {text: url, 'href':url})
                )
            )
        );


}

function deleteSeed(e){
    doc_id = e.target.getAttribute('data-value')

     $.ajax({
        type: 'POST',
        url: "/deleteSeed",
        data: {doc_id: doc_id},
        success: function(response) {
            console.log(response);
        }
     });
    e.target.parentElement.parentElement.remove()

}