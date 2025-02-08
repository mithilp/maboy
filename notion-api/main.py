from flask import Flask, request, jsonify
from datetime import datetime, timezone, date
import requests
import os

from dotenv import load_dotenv
import requests
load_dotenv()

app = Flask(__name__)

headers = {
    "Authorization": f"Bearer {os.environ["NOTION_TOKEN"]}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_pages():
    url = f"https://api.notion.com/v1/databases/{os.environ["DATABASE_ID"]}/query"
    payload = {"page_size": 100}
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    results = data["results"]
    return results

def update_page(page_id, properties):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"properties": properties}
    response = requests.patch(url, headers=headers, json=payload)
    return response.json()

@app.route('/get-tasks', methods=['GET'])
def get_today_tasks():
    pages = get_pages()
    today = date.today().isoformat()
    today_tasks = []
    
    for page in pages:
        props = page["properties"]
        due_date = props["due"]["date"]["start"]
        if due_date.startswith(today):
            task = {
                "id": page["id"],
                "name": props["Name"]["title"][0]["text"]["content"],
                "finished": props["Finished"]["checkbox"],
                "due": due_date
            }
            today_tasks.append(task)
    
    return jsonify(today_tasks)

@app.route('/update-task', methods=['POST'])
def update_task():
    data = request.json
    if not data or "id" not in data:
        return jsonify({"error": "Missing task ID"}), 400
    
    properties = {}
    if "name" in data:
        properties["Name"] = {"title": [{"text": {"content": data["name"]}}]}
    if "finished" in data:
        properties["Finished"] = {"checkbox": data["finished"]}
    if "due" in data:
        properties["due"] = {"date": {"start": data["due"]}}
    
    result = update_page(data["id"], properties)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
