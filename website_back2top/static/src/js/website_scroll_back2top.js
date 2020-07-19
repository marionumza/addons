$(document).ready(function() {
    var amountScrolled = 300;
    $('body').append('<a href="#" class="btn btn-secondary back-to-top">Back to Top</a>');

    $(window).scroll(function() {
        if ($(window).scrollTop() > amountScrolled) {
            $(document).find('a.back-to-top').fadeIn('slow');
        } else {
            $(document).find('a.back-to-top').fadeOut('slow');
        }
    });

    $(document).on('click', 'a.back-to-top', function() {
        $('body, html').animate({
            scrollTop: 0
        }, 500);
        return false;
    });
});
