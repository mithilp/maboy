import audioop
import base64
import json
import os
from flask import Flask, request
from flask_sock import Sock, ConnectionClosed
from twilio.twiml.voice_response import VoiceResponse, Start, Gather
from twilio.rest import Client
import vosk
import time

app = Flask(__name__)
sock = Sock(app)
twilio_client = Client()
model = vosk.Model("model")
global history
history = None
test="HELLO"
CL = '\x1b[0K'
BS = '\x08'

@app.route("/call", methods=['GET', 'POST'])
def call():
    response = VoiceResponse()
    response.say('Started')
    start = Start()
    start.stream(url=f'wss://{request.host}/stream')
    response.append(start)
    response.pause(length=12)
    print(f'Incoming call from {request.form["From"]}')
    response.redirect(f'/calendar')
    return str(response), 200, {'Content-Type': 'text/xml'}

@sock.route('/stream')
def stream(ws):
    """Receive and transcribe audio stream."""
    resp = VoiceResponse()
    rec = vosk.KaldiRecognizer(model, 16000)
    last_audio_time = time.time()
    response = ""
    while True:
        message = ws.receive()
        packet = json.loads(message)
        if packet['event'] == 'start':
            print('Streaming is starting')
            last_audio_time = time.time()
        elif packet['event'] == 'stop':
            print('\nStreaming has stopped')
        elif packet['event'] == 'media':
            audio = base64.b64decode(packet['media']['payload'])
            audio = audioop.ulaw2lin(audio, 2)
            audio = audioop.ratecv(audio, 2, 1, 8000, 16000, None)[0]

            # Calculate RMS volume
            rms = audioop.rms(audio, 2)  # 2 is the sample width in bytes
            
            if rms > 300:
                print("Audio activity detected")
                last_audio_time = time.time()
            
            if time.time() - last_audio_time > 5:
                print("\nNo significant audio detected for 3 seconds. Ending call.")
                break

            if rec.AcceptWaveform(audio):
                r = json.loads(rec.Result())
                response += CL + r['text'] + ' '
                print(CL + r['text'] + ' ', end='', flush=True)
            else:
                r = json.loads(rec.PartialResult())
                response += CL + r['partial'] + BS * len(r['partial'])
                print(CL + r['partial'] + BS * len(r['partial']), end='', flush=True)
    print("RESPONSE: ", response)
    # resp.redirect("/calendar")


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    # Start our TwiML response
    resp = VoiceResponse()
    gather = Gather(num_digits=1, action='/gather', method='POST')

    gather.say('Press 1.1 to interact with your google calendar agent.')
    print("ABOUT TO GATHER")
    resp.append(gather)
    return str(resp)

@app.route("/gather", methods=['GET', 'POST'])
def gather():
    digit_pressed = request.values.get('Digits')
    resp = VoiceResponse()
    if digit_pressed == '1':
        print("Calendar agent selected")
        resp.say("You've selected the calendar agent.")
        resp.redirect('/calendar')

    return str(resp)

@app.route("/calendar", methods=['GET', 'POST'])
def calendar_agent():
    print("IN CALENDAR AGENT")
    resp = VoiceResponse()
    gemini_response = {}
    try:
        gemini_response = call_gemini_agent()
        print("GEMINI RESPONSE: ", gemini_response)
        resp.say(gemini_response)
        if gemini_response.strip():  # Only say if there's actual content
            resp.say(gemini_response)
        else:
            resp.say("No response from calendar agent.")
    except Exception as e:
        print(f"Error calling Gemini agent: {e}")
        resp.say("Sorry, there was an error with the calendar agent.")
    resp.redirect('/call')
    return str(resp), 200, {'Content-Type': 'text/xml'}

def call_gemini_agent():

    import sys
    import json
    sys.path.append('/Users/anav/Desktop/Personal/maboy/calendar-api')
    
    try:
        from gemini import main
        print("Calling Gemini agent...")
        result = main()
        history = result['history']
        print("Gemini agent response:", result)
        return result['message']
    except Exception as e:
        print(f"Error importing/running Gemini agent: {e}")
        return None
    
    # import subprocess
    # print("Calling Gemini agent...")
    # process = subprocess.Popen(
    #     ['python3.12', '/Users/anav/Desktop/Personal/maboy/calendar-api/gemini.py'],
    #     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    # )
    # stdout, stderr = process.communicate(timeout=10)  # 10s timeout

    # if stderr:
    #     print(f"Gemini agent error: {stderr}")
    # print("Gemini agent response:", stdout)
    # return stdout
    # # print("Gemini agent response:", result.stdout)
    # # return result.stdout

@app.route("/", methods=['GET'])
def home():
    return "<h1>Welcome to the Twilio Voice API</h1>"

if __name__ == "__main__":
    app.run(debug=True, port=5002)