import requests
import json

def initialize_agent():
    print("main is starting")

    events = []  # Initialize events as an empty list

    # send a fetch request to the API endpoint /today-events to get today's events
    response = requests.get("http://127.0.0.1:5000/today-events")
    print("fetched url\n")
    if response.status_code == 200:
        print("successfully fetched events\n")
        events = response.json()
        print(events)
    else:
        print(f"Failed to fetch events. Status code: {response.status_code}")

    # start a chat session with the agent model
    chat_session = agent_model.start_chat(
      history=[
        {
          "role": "user",
          "parts": [
              json.dumps(events) + 
            "\n\nAbove is the list of today's events. What events do I have today?\n\nReply to the user by taking the JSON of the events and formatting it in a way that is easy to read and understand. For example, you could say something like \"You have 3 events today. The first event is a meeting with John at 10:00 AM. The second event is a lunch with Jane at 12:00 PM. The third event is a presentation at 2:00 PM.\"",
          ],
        },
      ])
    
    return chat_session

def process_response(chat_session, user_input):
    response = chat_session.send_message(user_input)

    message = json.loads(response.text)['message'] # say this out loud
    method = json.loads(response.text)['method'] # use this to determine next step

    output = f"method: {method}\n"

    # switch for each method
    if method == "talk":
        output += f"say out loud: {message}\n"
    elif method == "add":
        output += f"say out loud: {message}\n"
        add_event_payload = {
            "summary": json.loads(response.text)['summary'],
            "description": json.loads(response.text)['description'],
            "start": json.loads(response.text)['start'],
            "end": json.loads(response.text)['end'],
            "timeZone": json.loads(response.text).get('timeZone', 'America/New_York')
        }
        add_response = requests.post("http://127.0.0.1:5000/add-event", json=add_event_payload)
        if add_response.status_code == 201:
            output += "say out loud: Event added successfully.\n"
        else:
            output += "say out loud: Failed to add event.\n"
    elif method == "update":
        output += f"say out loud: {message}\n"
        update_event_payload = {
            "id": json.loads(response.text)['id'],
            "new_start_time": json.loads(response.text)['new_start_time'],
            "new_end_time": json.loads(response.text)['new_end_time'],
        }
        update_response = requests.patch(f"http://127.0.0.1:5000/update-event-time/{update_event_payload['id']}", json=update_event_payload)
        if update_response.status_code == 200:
            output += "say out loud: Event updated successfully.\n"
        else:
            output += "say out loud: Failed to update event.\n"
    elif method == "delete":
        output += f"say out loud: {message}\n"
        delete_event_payload = {
            "id": json.loads(response.text)['id']
        }
        delete_response = requests.delete(f"http://127.0.0.1:5000/delete-event/{delete_event_payload['id']}")
        if delete_response.status_code == 200:
            output += "say out loud: Event deleted successfully.\n"
        else:
            output += "say out loud: Failed to delete event.\n"
    elif method == "end":
        output += f"say out loud: {message}\n"
        output += "end call\n"
    else:
        output += "say out loud: something went wrong\n"

    return output

if __name__ == '__main__':
    chat_session = initialize_agent()
    while True:
        user_input = input("user: ")
        print(process_response(chat_session, user_input))