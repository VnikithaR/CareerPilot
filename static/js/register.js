
document.addEventListener("DOMContentLoaded", function () {
    const password = document.getElementById("password");
    const confirmPassword = document.getElementById("confirm_password");
    const message = document.getElementById("passwordMessage");
    const form = document.getElementById("registerForm");

    // Show/hide password
    document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
        button.addEventListener("click", function () {
            const fieldId = button.getAttribute("data-toggle-password");
            const field = document.getElementById(fieldId);

            if (!field) return;

            const shouldShow = field.type === "password";
            field.type = shouldShow ? "text" : "password";

            button.setAttribute("aria-pressed", String(shouldShow));
            button.setAttribute(
                "aria-label",
                shouldShow ? "Hide password" : "Show password"
            );

            const icon = button.querySelector("i");

            if (icon) {
                icon.classList.toggle("fa-eye", !shouldShow);
                icon.classList.toggle("fa-eye-slash", shouldShow);
            }
        });
    });

    function checkPasswords() {
        if (!password.value || !confirmPassword.value) {
            message.textContent = "";
            message.className = "form-hint";
            confirmPassword.setCustomValidity("");
            return true;
        }

        const matches = password.value === confirmPassword.value;

        message.textContent = matches
            ? "Passwords match."
            : "Passwords do not match.";

        message.className = matches
            ? "form-hint match"
            : "form-hint no-match";

        confirmPassword.setCustomValidity(
            matches ? "" : "Passwords do not match."
        );

        return matches;
    }

    password.addEventListener("input", checkPasswords);
    confirmPassword.addEventListener("input", checkPasswords);

    if (form) {
        form.addEventListener("submit", function (event) {
            if (!checkPasswords()) {
                event.preventDefault();
                confirmPassword.reportValidity();
            }
        });
    }
});