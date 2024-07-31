function sendEmail() {
    const verificationType = document.getElementById("identity_verification").value;
    const button = document.querySelector("[data-emails]");
    const emails = button.getAttribute("data-emails");
    const userEmail = button.getAttribute("data-user-email");
    const email_copy_id_verification_subject = button.getAttribute("email_copy_id_verification_subject");
    const email_copy_id_verification_body = button.getAttribute("email_copy_id_verification_body");
    const email_video_id_verification_subject = button.getAttribute("email_video_id_verification_subject");
    const email_video_id_verification_body = button.getAttribute("email_video_id_verification_body");

    let emailSubject, emailBody;

    if (verificationType === "email") {
        emailSubject = email_copy_id_verification_subject;
        emailBody = email_copy_id_verification_body;
    } else if (verificationType === "video") {
        emailSubject = email_video_id_verification_subject;
        emailBody = email_video_id_verification_body;
    }

    window.location.href = `mailto:${encodeURIComponent(userEmail)}?bcc=${encodeURIComponent(emails)}&subject=${encodeURIComponent(emailSubject)}&body=${encodeURIComponent(emailBody)}`;
    document.getElementById("submit_button").disabled = false;
}

document.addEventListener('DOMContentLoaded', () => {
    // Select all input fields with the names "password" or "password_confirm"
    const passwordInputs = document.querySelectorAll('input[name="password"], input[name="password_confirm"]');
    
    passwordInputs.forEach(input => {
        // Create a "Show/Hide" button with Bootstrap classes and Font Awesome icons
        const toggleButton = document.createElement('button');
        toggleButton.classList.add('btn', 'btn-outline-secondary');
        toggleButton.type = 'button';
        toggleButton.setAttribute('aria-label', 'Show Passwords');
        toggleButton.innerHTML = '<i class="fas fa-eye"></i>';

        // Wrap the input and the button in a flex container
        const wrapper = document.createElement('div');
        wrapper.classList.add('d-flex', 'align-items-center', 'position-relative');
        
        // Move the input and insert the button
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        wrapper.appendChild(toggleButton);

        // Add an event listener to the button
        toggleButton.addEventListener('click', () => {
            // Check the current type of the input field
            if (input.type === 'password') {
                input.type = 'text';
                toggleButton.setAttribute('aria-label', 'Hide Passwords');
                toggleButton.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else {
                input.type = 'password';
                toggleButton.setAttribute('aria-label', 'Show Passwords');
                toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });
    });
});
