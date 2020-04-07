"""
Author: Geovanni Hernandez
Local ZMA Async CLient paird with async_stream_marker_zmq_unity.py

 Using Async ZMQ to micmic example to create client for Unity client to  received marker data per frame
This will obtain the data from the Asyn Stream Marker ZMA Unity server which will send data per frame
"""
import zmq

from collections import namedtuple
import asyncio
import zmq.asyncio
from zmq.asyncio import Poller
addr = "tcp://127.0.0.1:7555"
# Socket to talk to server
context = zmq.Context.instance()
print("Connecting to Async Stream Marker ZMQ Unity Server>>>>>")


request = 0

async def receiver():
    global request
    pull = context.socket(zmq.PULL)
    pull.connect(addr)
    poller = Poller()
    poller.register(pull, zmq.POLLIN)
    while True:
        print("Sending request %s >>>\n" % request)
        events = await poller.poll()
        if pull in dict(events):

            messages_received =  pull.recv_multipart()
            for message_received in messages_received:
                print("<<< RECEIVED BYTES\n", message_received)
                unpacked_maessage_split = message_received.decode().split(",")
                print(f'MESSAGE DECODED SPLIT: {unpacked_maessage_split}\n')

        request += 1
asyncio.get_event_loop().run_until_complete(asyncio.wait([receiver()]))


