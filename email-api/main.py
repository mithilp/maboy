import datetime as dt
import os.path
from flask import Flask, jsonify, request
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.mime.text import MIMEText

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://mail.google.com/"]

app = Flask(__name__)

def get_gmail_service():
    """Get authenticated Gmail service."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return build("gmail", "v1", credentials=creds)

@app.route('/reply', methods=['POST'])
def reply_to_message():
    try:
        data = request.get_json()
        if not data or 'message_id' not in data or 'reply_text' not in data:
            return jsonify({"error": "message_id and reply_text are required"}), 400

        service = get_gmail_service()
        
        # Get the original message to extract headers
        original = service.users().messages().get(
            userId='me',
            id=data['message_id']
        ).execute()
        
        headers = original['payload']['headers']
        subject = next(
            (header["value"] for header in headers if header["name"] == "Subject"),
            "No subject"
        )
        # If subject doesn't start with Re:, add it
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
            
        # Get the sender's email to use as recipient
        sender = next(
            (header["value"] for header in headers if header["name"] == "From"),
            None
        )
        if not sender:
            return jsonify({"error": "Could not find original sender"}), 400

        # Create message
        message = MIMEText(data['reply_text'])
        message['to'] = sender
        message['subject'] = subject
        message['In-Reply-To'] = data['message_id']
        message['References'] = data['message_id']

        # Encode the message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send the reply
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': original['threadId']}
        ).execute()

        return jsonify({
            "message": "Reply sent successfully",
            "id": sent_message['id']
        })

    except HttpError as error:
        return jsonify({"error": str(error)}), 500

@app.route('/unread', methods=['GET'])
def get_unread_messages():
    try:
        service = get_gmail_service()
        
        # Calculate timestamp for 48 hours ago
        two_days_ago = (dt.datetime.now() - dt.timedelta(days=2)).strftime('%Y/%m/%d')
        
        results = service.users().messages().list(
            userId="me",
            q=f"is:unread after:{two_days_ago}"
        ).execute()
        
        messages = results.get("messages", [])
        if not messages:
            return jsonify({"messages": []})

        def get_message_body(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] in ['text/plain', 'text/html']:
                        if 'data' in part['body']:
                            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif 'body' in payload and 'data' in payload['body']:
                return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            return "No body content"

        unread_messages = []
        for message in messages:
            msg = service.users().messages().get(
                userId="me",
                id=message["id"]
            ).execute()
            
            headers = msg["payload"]["headers"]
            subject = next(
                (header["value"] for header in headers if header["name"] == "Subject"),
                "No subject"
            )
            sender = next(
                (header["value"] for header in headers if header["name"] == "From"),
                "No sender"
            )
            
            body = get_message_body(msg['payload'])
            
            unread_messages.append({
                "id": message["id"],
                "subject": subject,
                "sender": sender,
                "body": body
            })

        return jsonify({"messages": unread_messages})

    except HttpError as error:
        return jsonify({"error": str(error)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
