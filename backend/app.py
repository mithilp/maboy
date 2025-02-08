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

CL = '\x1b[0K'
BS = '\x08'

@app.route("/call", methods=['GET', 'POST'])
def call():
    response = VoiceResponse()
    response.say('Startypot.')
    start = Start()
    start.stream(url=f'wss://{request.host}/stream')
    response.append(start)
    response.say('Please leave a message')
    response.pause(length=60)
    print(f'Incoming call from {request.form["From"]}')
    return str(response), 200, {'Content-Type': 'text/xml'}

@sock.route('/stream')
def stream(ws):
    """Receive and transcribe audio stream."""
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
            # print(f"Received {len(audio)} bytes of audio")
            # print((not all(byte == 0 for byte in audio)))
            # if not all(byte == 0 for byte in audio):
            #         print("Audio detected")
            #         last_audio_time = time.time()

            # if time.time() - last_audio_time > 3: 
            #     print("\nNo audio detected for 3 seconds. Ending call.")
            #     break

            # Calculate RMS volume
            rms = audioop.rms(audio, 2)  # 2 is the sample width in bytes
            
            if rms > 300:
                print("Audio activity detected")
                last_audio_time = time.time()
            
            if time.time() - last_audio_time > 3:
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


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    # Start our TwiML response
    resp = VoiceResponse()
    gather = Gather(num_digits=1, action='/gather', method='POST')

    gather.say('Press 1.1 to interact with your google calendar agent.')
    print("ABOUT TO GATHER")
    resp.append(gather)
    resp.redirect('/voice')
    return str(resp)

@app.route("/gather", methods=['GET', 'POST'])
def gather():
    print("IN GATHER")
    digit_pressed = request.form.get('Digits')

    resp = VoiceResponse()
    resp.say("In gather")
    print("Digit pressed:", digit_pressed)
    if digit_pressed == '1':
        print("Calendar agent selected")
        resp.say("You've selected the calendar agent.")
        try:
            gemini_response = call_gemini_agent()
            if gemini_response.strip():  # Only say if there's actual content
                resp.say(gemini_response)
            else:
                resp.say("No response from calendar agent.")
        except Exception as e:
            print(f"Error calling Gemini agent: {e}")
            resp.say("Sorry, there was an error with the calendar agent.")

    else:
        resp.say("INVALID")
        resp.redirect('/voice')
    return str(resp)

def call_gemini_agent():
    import subprocess
    print("Calling Gemini agent...")
    process = subprocess.Popen(
        ['python3.12', '/Users/anav/Desktop/Personal/maboy/calendar-api/gemini.py'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = process.communicate(timeout=10)  # 10s timeout

    if stderr:
        print(f"Gemini agent error: {stderr}")
    print("Gemini agent response:", stdout)
    return stdout
    # print("Gemini agent response:", result.stdout)
    # return result.stdout

@app.route("/", methods=['GET'])
def home():
    return "<h1>Welcome to the Twilio Voice API</h1>"

if __name__ == "__main__":
    app.run(debug=True, port=5002)