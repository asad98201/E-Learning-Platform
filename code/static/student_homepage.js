const track = document.querySelector(".carousel-track");
const prevButton = document.querySelector(".prev");
const nextButton = document.querySelector(".next");
const slides = Array.from(track.children);
const slideWidth = slides[0].getBoundingClientRect().width;

let currentIndex = 0;

function moveToSlide(track, currentIndex) {
    track.style.transform = `translateX(-${slideWidth * currentIndex}px)`;
}

// Next button
nextButton.addEventListener("click", () => {
    currentIndex = (currentIndex + 1) % slides.length;
    moveToSlide(track, currentIndex);
});

// Previous button
prevButton.addEventListener("click", () => {
    currentIndex = (currentIndex - 1 + slides.length) % slides.length;
    moveToSlide(track, currentIndex);
});

const dropdownButtons = document.querySelectorAll(".dropdown-button");

dropdownButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
        const dropdown = event.target.closest(".dropdown");
        dropdown.classList.add("active");

        setTimeout(() => {
            dropdown.classList.remove("active");
        }, 2000); // Auto-hide after 2 seconds
    });
});

document.addEventListener("DOMContentLoaded", () => {
    const courseCards = document.querySelectorAll(".course-card");

    courseCards.forEach(card => {
        card.addEventListener("click", () => {
            const url = card.getAttribute("data-url");
            if (url) {
                window.location.href = url;
            }
        });
    });
});