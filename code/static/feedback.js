document.addEventListener("DOMContentLoaded", function() {
    // Add event listeners to feedback buttons
    const feedbackButtons = document.querySelectorAll('.feedback-btn');

    feedbackButtons.forEach(button => {
        button.addEventListener('click', function() {
            const courseId = this.getAttribute('data-course-id');
            const teacherId = this.getAttribute('data-teacher-id');
            openFeedbackPopup(courseId, teacherId);
        });
    });

    // Submit feedback function
    document.getElementById('submit-feedback').addEventListener('click', submitFeedback);
});

function openFeedbackPopup(courseId, teacherId) {
    // Store courseId and teacherId globally for use when submitting feedback
    window.selectedCourseId = courseId;
    window.selectedTeacherId = teacherId;

    // Display the feedback popup
    document.getElementById('feedback-popup').style.display = 'flex';
}

function closeFeedbackPopup() {
    // Hide the feedback popup when cancelled
    document.getElementById('feedback-popup').style.display = 'none';
}

function submitFeedback() {
    // Retrieve the feedback text from the textbox
    var feedbackText = document.getElementById('feedback-text').value;

    if (feedbackText.trim() === '') {
        alert('Please enter your feedback before submitting!');
        return;
    }

    // Prepare feedback data
    var feedbackData = {
        course_id: window.selectedCourseId,
        teacher_id: window.selectedTeacherId,
        feedback_text: feedbackText,
        student_id: 1,  // Use a placeholder for student_id
        feedback_id: Math.floor(Math.random() * 1000)  // Placeholder for Feedback ID
    };

    console.log('Feedback Submitted:', feedbackData); // For testing purposes

    // Close the popup after feedback is submitted
    closeFeedbackPopup();

    // Here, you can make an AJAX call to submit the feedback to the backend
    // Example: sendFeedbackToServer(feedbackData);
}