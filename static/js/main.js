
document.addEventListener("DOMContentLoaded", function () {
    // Display the current year in the footer
    const yearElement = document.getElementById("currentYear");

    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }

    // Close the mobile menu after selecting a navigation link
    const navbar = document.getElementById("mainNavbar");

    if (navbar && window.bootstrap) {
        const menu = bootstrap.Collapse.getOrCreateInstance(
            navbar,
            { toggle: false }
        );

        navbar.querySelectorAll(".nav-link").forEach(function (link) {
            link.addEventListener("click", function () {
                if (window.innerWidth < 992) {
                    menu.hide();
                }
            });
        });
    }
});