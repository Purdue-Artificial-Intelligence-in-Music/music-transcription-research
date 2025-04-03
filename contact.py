#!/opt/homebrew/bin/python3
"""
Name: contact.py
Purpose: Send emails to participants with their Google Drive folder details
"""

__author__ = "Ojas Chaturvedi"
__github__ = "github.com/ojas-chaturvedi"
__license__ = "MIT"


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Purdue's SMTP Relay Server
SMTP_SERVER = "smtp.purdue.edu"
SMTP_PORT = 25  # No authentication required when using Purdue's relay

# Sender email
FROM_EMAIL = "ochaturv@purdue.edu"


def send_email(name, email, folder_link, email_type):
    """
    Sends an email with Google Drive folder details.

    Args:
        name (str): Recipient's name.
        email (str): Recipient's email.
        folder_link (str): Link to the Google Drive folder.
        email_type (str): "new" for a new folder, "existing" if the folder already existed.
    """
    if not email:
        print(f"Skipping {name}: No email address provided.")
        return

    # Email subject and body variations
    if email_type == "new":
        subject = "Welcome to the 2025 Automatic Music Transcription Challenge!"
        body = f"""
        Hello {name},<br><br>

        Welcome, and thank you for participating in the 2025 Automatic Music Transcription (AMT) Challenge! 
        We have finished running your submitted model, and your results are now available for you to view. 
        You will find a Google Drive folder containing information regarding your model's results. 
        There, you can access:<br><br>

        - Your model's MP3 input</li><br>
        - Your model's output in MIDI file format</li><br>
        - Your model's output in PDF file format</li><br>
        - Statistics regarding your model's performance</li><br><br>
        - SLURM logs for your model's run</li><br>

        You can access it using the following link: <a href="{folder_link}">Click here to access your folder</a> <br>
        Or directly via this URL: {folder_link} <br><br>

        You are more than welcome to review your results, identify areas for improvement, and refine your model. 
        You can submit updated versions at any time before the submission deadline, 
        simply make sure the “Submission” tag remains on your release.<br><br>

        If you have any questions or need assistance, please don't hesitate to contact us at 
        <a href="mailto:ochaturv@purdue.edu">ochaturv@purdue.edu</a>.<br><br>

        Thank you again for participating in our competition!<br>
        AIM Research Team
        """
    else:  # "existing"
        subject = "AMT Challenge: Updated Results for Your Model"
        body = f"""
        Hello {name},<br><br>

        Thank you for participating in the 2025 AMT Challenge! We have re-run your submitted model, and 
        your updated results are available in the same Google Drive folder as your initial results, 
        in the link below:<br>
        <a href="{folder_link}">Click here to access your folder</a> <br>
        Or directly via this URL: {folder_link} <br><br>

        As always, you're encouraged to continue updating your model while submissions are open; 
        simply leave the “Submission” tag on the release!<br><br>

        If you have any questions or concerns, reach out to us at 
        <a href="mailto:ochaturv@purdue.edu">ochaturv@purdue.edu</a>.<br><br>

        Thank you again for participating in our competition!<br>
        AIM Research Team
        """

    # Create email message
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = email
    msg["Bcc"] = FROM_EMAIL  # BCC myself to keep a record
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        # Connect to Purdue SMTP relay
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.sendmail(FROM_EMAIL, [email, FROM_EMAIL], msg.as_string())
        server.quit()
        print(f"Email sent successfully to {name} ({email})")
    except Exception as e:
        print(f"Failed to send email to {name} ({email}): {e}")


if __name__ == "__main__":
    # Example usage
    send_email(
        name="John Doe",
        email="johndoe@example.com",
        folder_link="https://drive.google.com/drive/folders/EXAMPLE_FOLDER_ID",
        email_type="new",  # Use "existing" if the folder was already created
    )
