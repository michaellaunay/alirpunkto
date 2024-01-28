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
