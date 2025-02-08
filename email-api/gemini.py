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
  system_instruction="You are to assume the role of an email assistant with the task of helping the user manage their emails. You will communicate with the user and have access to functions to read unread emails, reply to emails, and delete emails.\n\nWhen prompted you must respond with JSON. One field must be on all responses called \"method\". method has 4 options: \"talk\", \"reply\", \"delete\", or \"end\". Another required field on all responses should be called \"message\".\n\n\"talk\" should be used when you are unsure of what the user is asking for, need to show them their unread emails, or if there is no other option here. If you set method to \"talk\", set the \"message\" field to a message you would send to the user to continue the conversation.\n\n\"reply\" will send a reply to an email. Your message field should be something like \"sending your reply\". Additionally, you will need to provide: \"message_id\" of the email being replied to, and \"reply_text\" containing the reply message. NEVER ask the user for a message_id as they won't have access to this. Instead, use context clues from their request (like the sender's name, subject, or content) to determine which email they're referring to. For example, if the user says 'reply to Jason's email about the meeting', you should find the message_id of the most recent email from Jason that mentions a meeting.\n\n\"delete\" will delete an email. Your message field should be something like \"deleting the email\". Additionally, you will need to provide the \"message_id\" of the email to delete. Like with replies, NEVER ask the user for a message_id. Use context clues from their request to determine which email they want to delete.\n\n\"end\" should be used when the user wants to end the conversation. When \"end\" is set as the \"method\", the \"message\" field should be set to a farewell message.",
)

def main():
    print("main is starting")

    # Get unread messages
    response = requests.get("http://127.0.0.1:5000/unread")
    if response.status_code == 200:
        emails = response.json()

    # start a chat session with the agent model
    chat_session = agent_model.start_chat(
      history=[
        {
          "role": "user",
          "parts": [
              json.dumps(emails) + 
            "\n\nAbove is the list of your unread emails from the last 48 hours. Would you like me to go through them?\n\nReply to the user by taking the JSON of the emails and formatting it in a way that is easy to read and understand. For example, you could say something like \"You have 3 unread emails. The first email is from John with subject 'Meeting Notes'. The second email is from Jane about 'Project Update'...\"",
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
        elif method == "reply":
            print("say out loud: ", message)
            reply_payload = {
                "message_id": json.loads(response.text)['message_id'],
                "reply_text": json.loads(response.text)['reply_text']
            }
            reply_response = requests.post("http://127.0.0.1:5000/reply", json=reply_payload)
            if reply_response.status_code == 200:
                print("say out loud: Reply sent successfully.")
            else:
                print("say out loud: Failed to send reply.")
            response = chat_session.send_message("Now, the user has the following message: " + input("user: "))
        elif method == "delete":
            print("say out loud: ", message)
            message_id = json.loads(response.text)['message_id']
            delete_response = requests.delete(f"http://127.0.0.1:5000/delete/{message_id}")
            if delete_response.status_code == 200:
                print("say out loud: Email deleted successfully.")
            else:
                print("say out loud: Failed to delete email.")
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