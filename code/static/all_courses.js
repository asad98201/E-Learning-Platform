document.addEventListener("DOMContentLoaded", () => {
    const courseCards = document.querySelectorAll(".course-card");
    const dropdownButtons = document.querySelectorAll(".dropdown-button");
    const filterButton = document.querySelector(".filter-button");

    // Course card click routing
    courseCards.forEach(card => {
        card.addEventListener("click", () => {
            const url = card.getAttribute("data-url");
            if (url) {
                window.location.href = url;
            }
        });
    });

    // Dropdown button functionality for navbar
    dropdownButtons.forEach(button => {
        const dropdown = button.parentElement;
        button.addEventListener("click", () => {
            dropdown.classList.toggle("active");
        });
    });

    // Filter dropdown functionality
    filterButton.addEventListener("click", () => {
        const filterMenu = document.querySelector(".filter-menu");
        filterMenu.style.display =
            filterMenu.style.display === "block" ? "none" : "block";
    });
});
