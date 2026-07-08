Original file in french at 
https://github.com/michaellaunay/alirpunkto/blob/master/docs/fr/Sc%C3%A9narios/Candidature.md

# Summary
Registration process for AlirPunkto.

# Actors

- The Applicant;
- Alirpunkto;
- The Open LDAP server;
- The mail server;
- The Administrator;
- Certified members with an active account.

# Steps

1. The Applicant logs into AlirPunkto;
2. AlirPunkto returns the homepage with the registration link;
3. The Applicant requests to create an account;
4. AlirPunkto offers the Applicant a choice between two options, presenting two buttons, each with a tooltip providing additional information about the meaning and implications of each of the two statuses:
    • ordinary member of the Community;
    • Cooperator.
5. The Applicant chooses one of the two options by clicking the corresponding button;
6. AlirPunkto requests the Applicant's email address;
7. The Applicant fills out this form;
8. AlirPunkto queries LDAP to verify that the email address is not already used by an active user or one who has canceled within less than the Quarantine period (Quantitative Parameter Affecting Internal Processes, the default value of which, defined in §3,4,1 of the statutes of Cosmopolitical.coop, is 180 days);
9. If the email address is already in use then : 
	1. AlirPunkto displays an error message indicating that this email address is already used and invites the Applicant to log in and abandons the application process
10. Else, if the email address is not in use (nominal case):
11. AlirPunkto creates an `application` object of type `Application` in the "Draft" state, with a unique `OID`, and records the information provided by the Applicant;
12. AlirPunkto saves the application in the database;
13. AlirPunkto randomly generates a very simple operation to solve in the form "(four + three) * (seven + five) + two" (Multiplication of the sum of two numbers between 2 and 9 written in full added to a number between 1 and 9 in full);
14. AlirPunkto records the expected solution in the `application` object.
15. AlirPunkto prepares an email for the Applicant containing the operation to solve and the link to return to the form if necessary.
16. AlirPunkto sends the email to the Applicant;
17. AlirPunkto changes the state of the `application` to "EmailValidation";
18. AlirPunkto saves the `application` in the database;
19. AlirPunkto determines the expiry date of the Application (the time given to the Applicant to open their email, perform the calculation, and return the result via the form);
20. AlirPunkto schedules a cleanup task for the `application` if the expiry is reached without email validation from the Applicant;
21. AlirPunkto displays a message informing the Applicant that they will receive an email containing a simple mathematical operation to solve, and the result must be entered before the expiry date in the verification field of the page to which the link provided in the upcoming email will grant access;
22. The Applicant opens the received email in their email client.
23. The Applicant performs the required calculation.
24. The Applicant enters the result into the form on the page accessed via the provided link in the email and submits it.
25. AlirPunkto verifies the result.
26. As long as the result is not correct:
    1. AlirPunkto displays an error message.
    2. AlirPunkto requests the result again, allowing a maximum of 3 attempts.
    3. If there are 3 errors:
        1. AlirPunkto displays a message of abandonment and stops the process.
        2. AlirPunkto returns to the homepage.
        3. End of scenario.
27. If the result is correct then:
28. AlirPunkto deletes the planned cleanup task and changes the Application status to "ConfirmedHuman".
29. AlirPunkto displays the registration form, pre-filling the email field which can no longer be modified.
30. The Applicant enters the requested information, namely:
    • their pseudonym (with a tooltip – already written – informing them that this pseudonym can never be changed and it shouldn't be possible to trace back to their real identity with it);
    • their password (according to ticket #84 of Cosmopoliticalcoop project — Enter the password upon registration - and avoid an unnecessary step);
    • their preferred language of interaction (among the 23 official languages of the European Union + Esperanto, English by default);
    • their 2nd preferred language of interaction (same) - optional data;
    • their 3rd preferred language of interaction (same) - optional data;
    • their user profile text – optional data;
    • their display picture/avatar – optional data;
    • and, only if the Applicant chose the "Cooperator" option:
        ◦ their first names transcribed in Latin characters if needed (for Greek and Bulgarian), as they appear in their official documents;
        ◦ their surnames, similarly;
        ◦ their date of birth;
        ◦ their nationality (from the Member States of the European Union);
31. The Applicant submits the form.
32. AlirPunkto checks the syntax of the entries.
33. AlirPunkto queries the LDAP to verify that the pseudonym is not already used by an active user or one who has resigned less than the Quarantine period (Quantitative Parameter Affecting Internal Processes).
34. As long as the pseudonym is already in use, AlirPunkto displays an error message indicating that this pseudonym is already taken and invites the Applicant to choose another pseudonym.
35. If the Applicant has chosen the "Ordinary Community Member" option, then:
    • 1. The Applicant becomes an "Ordinary Community Member".
    • 2. AlirPunkto determines the membership number of the new member.
    • 3. AlirPunkto adds an entry in the LDAP.
    • 4. AlirPunkto sends a congratulatory email to the new member.
    • 5. AlirPunkto changes the `candidature` status to `ApprovedOrdinaryCommunityMember`.
36. Else [if the Applicant has chosen the "Cooperator" option], the following procedure is carried out (nominal case):
37. AlirPunkto queries the LDAP to ensure that the combination of names, first names, and date of birth is not already used by an active user or one who has resigned less than the Quarantine period (Quantitative Parameter Affecting Internal Processes).
38. If the combination of names, first names, and date of birth is already in use, then the Applicant is already registered:
    1. AlirPunkto displays an error message and invites the Applicant to log in, abandoning the application procedure.
39. If the Applicant is not already registered:
40. AlirPunkto sets the `candidature` status to `UniqueData`.
41. AlirPunkto records the date.
42. AlirPunkto saves this object in the database.
43. AlirPunkto displays the application submission view, which warns the Applicant that they will either have to send a copy of their ID by email or show it in a video conference to N verifiers (N = the number of Verifiers, a Quantitative Parameter Affecting Internal Processes, with the default value defined in §3.4.1 of the statutes, being 3).
44. The Applicant accepts the submission.
45. AlirPunkto informs the Applicant that their ID will either need to be sent to the verifiers or that they should make separate appointments with each one.
46. AlirPunkto randomly selects N verifiers from active LDAP members if possible, otherwise the administrator.
47. AlirPunkto records the verifiers in the `verifiers` dictionary of the `candidature`.
48. AlirPunkto logs the submission date in the `candidature`.
49. AlirPunkto sets the `candidature` status to "Pending".
50. AlirPunkto adds a "votes" attribute, which is an empty dictionary, to the `candidature`.
51. AlirPunkto saves the changes of the candidature object in the database.
52. AlirPunkto sends an email to the verifiers requesting a vote (using the vote.pt template and passing the candidature's ID) to accept or reject the application, explaining the procedure and including the voting link.
53. If the email sending fails, the site logs an error message and attempts to send an email to the administrator.
54. AlirPunkto sends a page to the Applicant's browser containing two buttons to choose their identity verification method: (1) by video conference or (2) by email attachment.
55. The Applicant selects their identity verification method and clicks the corresponding button.
56. If the Applicant chooses the "by video conference" method, then:
    1. AlirPunko sends a page to the Applicant's browser containing a button to assist in writing the email.
    2. This button contains a "mailto" link that opens the Applicant's email addressed to the Applicant, with the Verifiers in blind copy (BCc field), with a pre-filled subject and body in the Applicant's preferred language, inviting the Verifier to select a date and time slot for the video conference among those offered by the Applicant (which the Applicant determines, before a deadline for submitting identity data equal to a configurable notice period before the verifiers' voting end date), and containing links to free video conferencing services.
    3. The Applicant clicks the button, adds to the pre-filled email the proposed appointment dates and times, and a video conference link, and sends the email to all Verifiers at once.
57. Else, [if the Applicant chose the "by email attachment" verification method]:
    1. AlirPunko sends a page to the Applicant's browser containing a button to assist in writing the email.
    2. This button contains a "mailto" link that opens the Applicant's email addressed to the Applicant, with the Verifiers in blind copy (BCc field), with a pre-filled subject and body in the Applicant's preferred language to accompany the sending of the partial copy of the ID.
    3. The Applicant clicks the button, attaches to the pre-filled email an incomplete copy of their official identity document (e.g., masking the number and place of birth) and sends the email to all Verifiers at once.
58. Each of the verifiers receives the incomplete copy of the identity document or views it during the video conference and checks the conformity of the identity information provided by the Applicant during their registration (nationality, names, surnames, date of birth) with those of the official identity document.
59. Each verifier checks the integrity of the Applicant's information by connecting to AlirPunkto via the link from the email received from AlirPunkto.
60. AlirPunkto prompts the verifier to authenticate.
61. The verifier authenticates themselves.
62. AlirPunkto displays the voting view containing the Applicant's information.
63. The verifier either accepts or rejects the application.
64. AlirPunkto records the verifier's choice.
65. If the last verifier has voted or if the closing date is reached, then AlirPunkto determines whether the application is accepted or not (refused by default if no Verification is done by the closing date).
66. AlirPunkto records the result in the `candidature` and saves it in the database.
67. If the majority accepts the application:
	1. The Applicant becomes a "Cooperator".
	2. AlirPunkto determines the member number of the new member.
	3. AlirPunkto adds an entry in LDAP.
	4. AlirPunkto sets the `candidature` status to `ApprovedCooperator`.
68. If it is rejected:
	1. AlirPunkto sets the `candidature` status to `Refused`.
	2. AlirPunkto saves the `candidature` in the database.
69. AlirPunkto sends either a rejection or acceptance email to the new member, depending on the final status of the application. 

# Alternative Scenarios
## The Applicant doesn’t receive the email or never confirms

The AlirPunkto scheduler searches for `candidatures` in the "EmailValidation" state reaching 1 day from the deadline and reminds the candidate.

## Reminder for Verifiers

The AlirPunkto scheduler searches for `candidatures` in the "Pending" state reaching 1 day from the deadline; 
AlirPunkto sends a reminder email to the verifiers.

## Reaching the Voting Deadline

The AlirPunkto scheduler searches for `candidatures` in the "Pending" state that have reached the deadline; 

If the application has received more favorable votes, then it receives favorable treatment (see above). 
Else, it's treated as a refusal.

## Interruption During the Process

A disruption prevented the Applicant from finishing the submission process.
The Applicant activates the link from one of the emails received during the process by Alirpunkto and resumes the process from the last recorded state in the application.

# Additional Information
## Application States

1. Draft: The application is in draft mode.
2. Email Validation: The state where the Applicant's email address is awaiting validation.
3. ConfirmedHuman: The Applicant's email address is verified, and humanity proof is provided.
4. UniqueData: The Applicant has entered their personal identification data.
5. Pending: After the submission of the application and while waiting for verification by the verifiers.
6. Approved: The application has been accepted.
7. Refused: The application has been denied.
