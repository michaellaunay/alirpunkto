function sendEmail() {
    const verificationType = document.getElementById("identity_verification").value;
    const button = document.querySelector("[data-emails]");
    const emails = button.getAttribute("data-emails");

    let emailSubject, emailBody;

    if (verificationType === "email") {
        emailSubject = "Copy of Identity Verification";
        emailBody = "Please find attached the copy of your identity verification.";
    } else if (verificationType === "video") {
        emailSubject = "Video Conference for Identity Verification";
        emailBody = "Please click on the link below to join the video conference for your identity verification.";
    }

    window.location.href = `mailto:?cc=${encodeURIComponent(emails)}&subject=${encodeURIComponent(emailSubject)}&body=${encodeURIComponent(emailBody)}`;
}
