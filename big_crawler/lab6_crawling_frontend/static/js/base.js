// Adds some custom functionality to the base.html layout, which is available
// in all views.
// Author: Johannes Mueller <j.mueller@reply.de>

function smoothScrollToTop(event) {
    var position = $("#topAnchor").offset().top;
    $("html").animate({scrollTop: position}, "1000");
    event.preventDefault();
}

$(".btn-top").click(smoothScrollToTop);