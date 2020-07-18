$(document).ready(function () {
    $(".as_our_blog").owlCarousel({
        items: 2,
        margin: 10,
        nav: true,
        pagination: false,
        responsive: {
            0: {
                items: 1,
            },
            481: {
                items: 1,
            },
            768: {
                items: 2,
            },
            1024: {
                items: 2,
            }
        }

    });
    $("#medical-team").owlCarousel({
        items: 3,
        nav: true,
        pagination: true,
        autoPlay:true,
        responsive: {
            0: {
                items: 1,
            },
            481: {
                items: 1,
            },
            768: {
                items: 2,
            },
            1024: {
                items: 3,
            }
        }

    });

    if ($(".chartjs-render-monitor").length !== 0) {
        var randomScalingFactor = function () {
            return Math.round(Math.random() * 100);
        };

        var config = {
            type: 'pie',
            data: {
                datasets: [{
                    data: [
                        randomScalingFactor(),
                        randomScalingFactor(),
                        randomScalingFactor(),
                        randomScalingFactor(),
                    ],
                    backgroundColor: [
                        window.chartColors.red,
                        window.chartColors.orange,
                        window.chartColors.green,
                        window.chartColors.blue,
                    ],
                    label: 'Dataset 1'
                }],
                labels: [
                    "Red",
                    "Orange",
                    "Green",
                    "Blue"
                ]
            },
            options: {
                responsive: true
            }
        };

        window.onload = function () {
            var ctx = document.getElementById("chart-area").getContext("2d");
            window.myPie = new Chart(ctx, config);
        };
    }
});
/*
$(document).ready(function () {
// When the user scrolls the page, execute myFunction
    window.onscroll = function () {
        myFunction()
    };

// Get the navbar
    var navbar = document.getElementById("fix_top");

// Get the offset position of the navbar
    var sticky = navbar.offsetTop;

// Add the sticky class to the navbar when you reach its scroll position. Remove "fixed-top" when you leave the scroll position
    function myFunction() {
        if (window.pageYOffset >= sticky) {
            navbar.classList.add("fixed-top")
        } else {
            navbar.classList.remove("fixed-top");
        }
    }
});
*/
