function sendEmail() {
    const verificationType = document.getElementById("identity_verification").value;
    const button = document.querySelector("[data-emails]");
    const emails = button.getAttribute("data-emails");
    const userEmail = button.getAttribute("data-user-email");
    const votingUrl = button.getAttribute("data-voting-url");
    const signature = button.getAttribute("data-signature");

    let emailSubject, emailBody;

    if (verificationType === "email") {
        emailSubject = "Copy of Identity Verification";
        emailBody = `Dear Voter,

        We kindly request you to validate the identity of our member. Once validated, we invite you to cast your vote using the link below:
        
        ${votingUrl}
        
        Thank you for your prompt attention to this matter. Your participation is crucial to our community.
        
        Warm regards,
        ${signature}`;
    } else if (verificationType === "video") {
        emailSubject = "Video Conference for Identity Verification";
        emailBody = `Dear Voter,

        We have scheduled a video conference for the purpose of member identity verification. Post verification, please use the link below to cast your vote:
        
        ${votingUrl}
        
        Looking forward to seeing you in the video conference. Your involvement is valuable to us.
        
        Best wishes,
        ${signature}`;
    }

    window.location.href = `mailto:${encodeURIComponent(userEmail)}?bcc=${encodeURIComponent(emails)}&subject=${encodeURIComponent(emailSubject)}&body=${encodeURIComponent(emailBody)}`;
}
