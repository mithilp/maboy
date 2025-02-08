import audioop
import base64
import json
import os
from flask import Flask, request
from flask_sock import Sock, ConnectionClosed
from twilio.twiml.voice_response import VoiceResponse, Start
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
            if not all(byte == 0 for byte in audio):
                    last_audio_time = time.time()

            if time.time() - last_audio_time > 3: 
                print("\nNo audio detected for 3 seconds. Ending call.")
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
    """Respond to incoming phone calls with a 'Hello world' message"""
    # Start our TwiML response
    resp = VoiceResponse()

    # Read a message aloud to the caller
    resp.say("Hello world!")

    return str(resp)

@app.route("/", methods=['GET'])
def home():
    return "<h1>Welcome to the Twilio Voice API</h1>"

if __name__ == "__main__":
    app.run(debug=True)