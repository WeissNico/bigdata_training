jQuery(document).ready(function($) {
$('.table > tbody > tr').on('click',function() {
    // row was clicked
    $(this).addClass('active');
});
});