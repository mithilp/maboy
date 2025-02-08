import os
import google.generativeai as genai
import json

from dotenv import load_dotenv
import requests
load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "application/json",
}

agent_model = genai.GenerativeModel(
  model_name="gemini-2.0-flash",
  generation_config=generation_config,
  system_instruction="You are to assume the role of an employee with the sole task of helping the user manage their calendar. You will be in charge of communicating with the user and you will also have access to 3 functions to add, update, or delete the user's calendar events. \n\n\nwhen prompted you must response with JSON. one field must be on all responses and it should be called \"method\". method has 5 options: \"talk\", \"add\", \"update\", \"delete\", or \"end\". another required field on all responses should be called \"message\"\n\n\n\"talk\" should be used when you are unsure of what the user is asking for or if there is no other option here. if you set method to \"talk\", set the \"message\" field to a message you would send to the user to continue the conversation.\n\n\"add\" will add an event to the user's calendar. your message field should be something along the lines of \"adding event to your calendar.\" additionally, you will need to provide the following fields: \"summary,\" \"description\", \"start\" which represents the start time of the event, and \"end\" which represents the end time of the event \n\n\"update\" will update an event in the user's calendar.  your message field should be something along the lines of \"updating event in your calendar.\" additionally, you will need to provide the following fields: \"id\" representing the id of the event you need to update, along with \"new_start_time\" which represents the start time of the event and \"new_end_time\" which represents the end time of the event\n\n\"delete\" will delete an event in the user's calendar. your message field should be something along the lines of \"deleting event from your calendar.\" additionally, you will need to provide the following fields: \"id\" representing the id of the event you need to delete\n\n\"end\" should be used when the user wants to end the conversation and says something along the lines of \"Thank you so much for your help\" or \"Goodbye\". when \"end\" is set as the \"method\", the \"message\" field should be set to something along the lines of \"you're welcome it was great talking!\"",
    )

def initialize_history():
    # send a fetch request to the API endpoint /today-events to get today's events
    response = requests.get("http://127.0.0.1:5000/today-events")
    if response.status_code == 200:
        events = response.json()

    return [
        {
          "role": "user",
          "parts": [
              json.dumps(events) + 
            "\n\nAbove is the list of today's events. What events do I have today?\n\nReply to the user by taking the JSON of the events and formatting it in a way that is easy to read and understand. For example, you could say something like \"You have 3 events today. The first event is a meeting with John at 10:00 AM. The second event is a lunch with Jane at 12:00 PM. The third event is a presentation at 2:00 PM.\"",
          ],
        },
      ]

def main(user_message=None, history=None):
    print("main is starting")

    if not user_message or len(user_message) < 2:
        user_message = "INSERT_INPUT_HERE"
    print("user message: ", user_message)

    if history is None:
        history = initialize_history()
    
    # print(events)
    # start a chat session with the agent model
    chat_session = agent_model.start_chat(
        history=history
    )
    
    response = chat_session.send_message(user_message)

    ended = False
    print(json.loads(response.text)['message'])

    message = json.loads(response.text)['message'] # say this out loud
    method = json.loads(response.text)['method'] # use this to determine next step

    print("method:", method)

    # switch for each method
    if method == "talk":
        print("say out loud: ", message)
    elif method == "add":
        print("say out loud: ", message)
        add_event_payload = {
            "summary": json.loads(response.text)['summary'],
            "description": json.loads(response.text)['description'],
            "start": json.loads(response.text)['start'],
            "end": json.loads(response.text)['end'],
            "timeZone": json.loads(response.text).get('timeZone', 'America/New_York'),
        }
        add_response = requests.post("http://127.0.0.1:5000/add-event", json=add_event_payload)
        if add_response.status_code == 201:
            print("say out loud: Event added successfully.")
        else:
            print("say out loud: Failed to add event.")
    elif method == "update":
        print("say out loud: ", message)
        update_event_payload = {
            "id": json.loads(response.text)['id'],
            "new_start_time": json.loads(response.text)['new_start_time'],
            "new_end_time": json.loads(response.text)['new_end_time'],
        }
        update_response = requests.patch(f"http://127.0.0.1:5000/update-event-time/{update_event_payload['id']}", json=update_event_payload)
        if update_response.status_code == 200:
            print("say out loud: Event updated successfully.")
        else:
            print("say out loud: Failed to update event.")
    elif method == "delete":
        print("say out loud: ", message)
        delete_event_payload = {
            "id": json.loads(response.text)['id']
        }
        delete_response = requests.delete(f"http://127.0.0.1:5000/delete-event/{delete_event_payload['id']}")
        if delete_response.status_code == 200:
            print("say out loud: Event deleted successfully.")
        else:
            print("say out loud: Failed to delete event.")
    elif method == "end":
        print("say out loud:", message)
        ended = True
        print("end call")
    else:
        print("say out loud: something went wrong")
        ended = True

    return {'message': message, 'history': chat_session.history, 'ended': ended}