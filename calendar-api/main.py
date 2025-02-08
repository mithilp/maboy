import datetime as dt
import os.path
from flask import Flask, jsonify, request
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']
app = Flask(__name__)

def get_credentials():
  creds = None
  if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json')
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
      creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
      token.write(creds.to_json())
  return creds

@app.route('/today-events', methods=['GET'])
def today_events():
  creds = get_credentials()
  try:
    service = build('calendar', 'v3', credentials=creds)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    end_of_day = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    events_result = service.events().list(
      calendarId='primary', timeMin=now, timeMax=end_of_day,
      singleEvents=True, orderBy='startTime').execute()

    events = events_result.get("items", [])
    if not events:
      return jsonify({"message": "No upcoming events found."}), 200

    return jsonify(events), 200

  except HttpError as e:
    return jsonify({"error": str(e)}), 500

@app.route('/add-event', methods=['POST'])
def add_event():
    print("test")
    creds = get_credentials()
    try:
        service = build('calendar', 'v3', credentials=creds)
        data = request.get_json()

        # Set default values for optional fields
        event = {
            'summary': data.get('summary', 'Untitled Event'),
            'location': data.get('location', ''),
            'description': data.get('description', ''),
            'start': {
                'dateTime': data.get('start_time', dt.datetime.now(dt.timezone.utc).isoformat()),
                'timeZone': data.get('timezone', 'UTC'),
            },
            'end': {
                'dateTime': data.get('end_time', (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat()),
                'timeZone': data.get('timezone', 'UTC'),
            },
            'reminders': {
                'useDefault': data.get('use_default_reminders', True),
                'overrides': data.get('reminders', [])
            },
            'attendees': data.get('attendees', []),
            'colorId': data.get('color_id', '1')
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return jsonify(event), 201

    except HttpError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
  app.run(port=5000, debug=True)