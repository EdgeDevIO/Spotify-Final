import imaplib
import email
from email.header import decode_header


def connect_to_gmail_imap(user, password, log):
	"""
	Connect to the Gmail IMAP server and log in using the provided credentials.
	
	Parameters:
		user (str): The username (email address) for Gmail.
		password (str): The password for the Gmail account.
		
	Returns:
		IMAP4_SSL: An imaplib IMAP4_SSL object with the 'Inbox' selected.
		
	Raises:
		imaplib.IMAP4.error: If there are issues during the login or selecting the inbox.
		Exception: For handling other unexpected errors.
	"""
	imap_url = 'imap.gmail.com'
	try:
		my_mail = imaplib.IMAP4_SSL(imap_url)
		my_mail.login(user, password)
		my_mail.select('Inbox')
		log.debug("Connected to Gmail and selected Inbox successfully.")
		return my_mail
	except imaplib.IMAP4.error as e:
		log.debug(f"Error during IMAP login or Inbox selection: {e}")
		raise
	except Exception as e:
		log.debug(f"Unexpected error: {e}")
		raise


def fetch_confirmation_code(user, password, log):
	"""
	Fetch the Spotify confirmation code from Gmail.
	
	Parameters:
		user (str): The username (email address) for Gmail.
		password (str): The password for the Gmail account.
		
	Returns:
		str: The extracted confirmation code if found, otherwise None.
	"""
	try:
		# Connect to Gmail
		mail = connect_to_gmail_imap(user, password, log)

		# Search for all emails in the mailbox
		status, messages = mail.search(None, "ALL")
		if status != "OK":
			log.debug("No messages found!")
			return None

		# Convert messages to a list of email IDs
		email_ids = messages[0].split()
		
		# Fetch the latest emails
		for email_id in email_ids[-10:]:  # Adjust range if needed
			# Fetch the email by ID
			status, msg_data = mail.fetch(email_id, "(RFC822)")
			if status != "OK":
				log.debug(f"Failed to fetch email ID {email_id.decode()}")
				continue

			# Parse the raw email content
			for response_part in msg_data:
				if isinstance(response_part, tuple):
					# Decode the email bytes to a message object
					msg = email.message_from_bytes(response_part[1])
					# Decode the email subject
					subject, encoding = decode_header(msg["Subject"])[0]
					if isinstance(subject, bytes):
						# If it's a bytes, decode to str
						subject = subject.decode(encoding if encoding else "utf-8")
					# Get the sender's email address
					from_ = msg.get("From")

					# If the email message is multipart
					if msg.is_multipart():
						# Iterate over email parts
						for part in msg.walk():
							# If the part is the email body
							if part.get_content_type() == "text/plain":
								# Decode the email body
								body = part.get_payload(decode=True).decode()
					else:
						# If it's a single-part email
						body = msg.get_payload(decode=True).decode()

					# Check for Spotify confirmation email
					if subject == 'Confirm your account' and 'spotify' in from_:
						mail.close()
						mail.logout()
						return (body.split('(')[1].split(')')[0]).strip()

		# Close the mailbox and logout
		mail.close()
		mail.logout()

	except Exception as e:
		log.debug(f"An error occurred: {e}")
		return None


# from email_fetcher import fetch_confirmation_code

# Replace with your Gmail credentials
# username = "ShilaDelagarza781992Hvo@gmail.com"
# password = "keaoxwezrvuktxfa"

# # Fetch the confirmation code
# confirmation_code = fetch_confirmation_code(username, password)

# if confirmation_code:
#     log.debug(f"Confirmation Code: {confirmation_code}")
# else:
#     log.debug("No confirmation code found.")