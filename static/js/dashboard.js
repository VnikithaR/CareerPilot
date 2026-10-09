
document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("dashboardSidebar");
    const toggle = document.getElementById("sidebarToggle");
    const overlay = document.getElementById("sidebarOverlay");
    const year = document.getElementById("currentYear");

    if (year) {
        year.textContent = new Date().getFullYear();
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("sidebar-open");
        if (overlay) overlay.classList.remove("overlay-visible");
    }

    if (toggle && sidebar && overlay) {
        toggle.addEventListener("click", function () {
            sidebar.classList.toggle("sidebar-open");
            overlay.classList.toggle("overlay-visible");
        });

        overlay.addEventListener("click", closeSidebar);

        sidebar.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", closeSidebar);
        });
    }
});