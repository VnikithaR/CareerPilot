
document.addEventListener("DOMContentLoaded", function () {
    const password = document.getElementById("password");
    const toggleButton = document.getElementById("togglePassword");
    const showCheckbox = document.getElementById("showPasswordCheckbox");

    function setPasswordVisibility(visible) {
        password.type = visible ? "text" : "password";

        toggleButton.setAttribute("aria-pressed", String(visible));
        toggleButton.setAttribute(
            "aria-label",
            visible ? "Hide password" : "Show password"
        );

        const icon = toggleButton.querySelector("i");

        icon.classList.toggle("fa-eye", !visible);
        icon.classList.toggle("fa-eye-slash", visible);

        showCheckbox.checked = visible;
    }

    toggleButton.addEventListener("click", function () {
        setPasswordVisibility(password.type === "password");
    });

    showCheckbox.addEventListener("change", function () {
        setPasswordVisibility(showCheckbox.checked);
    });
});