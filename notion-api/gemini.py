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
  system_instruction="You are to assume the role of an employee with the sole task of helping the user manage their Notion tasks database. You will be in charge of communicating with the user and you will also have access to 3 functions to add, update, or delete tasks. \n\n\nwhen prompted you must response with JSON. one field must be on all responses and it should be called \"method\". method has 5 options: \"talk\", \"add\", \"update\", \"delete\", or \"end\". another required field on all responses should be called \"message\"\n\n\n\"talk\" should be used when you are unsure of what the user is asking for or if there is no other option here. if you set method to \"talk\", set the \"message\" field to a message you would send to the user to continue the conversation.\n\n\"add\" will add a task to the database. your message field should be something along the lines of \"adding task to your database.\" additionally, you will need to provide the following fields: \"Name\", \"due\", and \"Finished\" \n\n\"update\" will update a task in the database.  your message field should be something along the lines of \"updating task in your database.\" additionally, you will need to provide the following fields: \"id\" representing the id of the task you need to update, along with \"Name\", \"due\", and \"Finished\"\n\n\"delete\" will delete a task from the database. your message field should be something along the lines of \"deleting task from your database.\" additionally, you will need to provide the following fields: \"id\" representing the id of the task you need to delete\n\n\"end\" should be used when the user wants to end the conversation and says something along the lines of \"Thank you so much for your help\" or \"Goodbye\". when \"end\" is set as the \"method\", the \"message\" field should be set to something along the lines of \"you're welcome it was great talking!\"",
)

def main():
    print("main is starting")

    # Get today's tasks instead of events
    response = requests.get("http://127.0.0.1:5000/get-tasks")
    if response.status_code == 200:
        tasks = response.json()

    # start a chat session with the agent model
    chat_session = agent_model.start_chat(
      history=[
        {
          "role": "user",
          "parts": [
              json.dumps(tasks) + 
            "\n\nAbove is the list of today's tasks. What tasks do I have today?\n\nReply to the user by taking the JSON of the tasks and formatting it in a way that is easy to read and understand. For example, you could say something like \"You have 3 tasks today. The first task is to complete the report (not finished, due at 10:00 AM). The second task is to review code (finished, due at 2:00 PM).\"",
          ],
        },
      ])
    
    response = chat_session.send_message("INSERT_INPUT_HERE")

    ended = False

    while not ended:
        message = json.loads(response.text)['message']
        method = json.loads(response.text)['method']

        print("method:", method)

        if method == "talk":
            print("say out loud: ", message)
            response = chat_session.send_message("Now, the user has the following message: " + input("user: "))
        elif method == "add":
            print("say out loud: ", message)
            add_task_payload = {
                "name": json.loads(response.text)['Name'],
                "due": json.loads(response.text)['due'],
                "finished": json.loads(response.text).get('Finished', False)
            }
            add_response = requests.post("http://127.0.0.1:5000/add-task", json=add_task_payload)
            if add_response.status_code == 200:
                print("say out loud: Task added successfully.")
            else:
                print("say out loud: Failed to add task.")
            response = chat_session.send_message("Now, the user has the following message: " + input("user: "))
        elif method == "update":
            print("say out loud: ", message)
            update_task_payload = {
                "id": json.loads(response.text)['id']
            }
            # Only include fields that are being updated
            if 'Name' in json.loads(response.text):
                update_task_payload['name'] = json.loads(response.text)['Name']
            if 'due' in json.loads(response.text):
                update_task_payload['due'] = json.loads(response.text)['due']
            if 'Finished' in json.loads(response.text):
                update_task_payload['finished'] = json.loads(response.text)['Finished']
            
            update_response = requests.post("http://127.0.0.1:5000/update-task", json=update_task_payload)
            if update_response.status_code == 200:
                print("say out loud: Task updated successfully.")
            else:
                print("say out loud: Failed to update task.")
            response = chat_session.send_message("Now, the user has the following message: " + input("user: "))
        elif method == "delete":
            print("say out loud: ", message)
            delete_task_payload = {
                "id": json.loads(response.text)['id']
            }
            delete_response = requests.delete(f"http://127.0.0.1:5000/delete-task/{delete_task_payload['id']}")
            if delete_response.status_code == 200:
                print("say out loud: Task deleted successfully.")
            else:
                print("say out loud: Failed to delete task.")
            response = chat_session.send_message("Now, the user has the following message: " + input("user: "))
        elif method == "end":
            print("say out loud:", message)
            ended = True
            print("end call")
        else:
            print("say out loud: something went wrong")
            ended = True

if __name__ == '__main__':
    main()