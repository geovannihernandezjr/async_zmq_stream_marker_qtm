"""
Author: Geovanni Hernandez
Async Stream Marker ZMQ Unity
 Using Qualisys python SDK 'qtm' which uses async programming in python
 Using Async ZMQ to create server for Unity client to connect to received marker data per frame

 To run locally must use local_zmq_async_client:
 1. Open QTM  --> Select No Project (when UI asks for project)
 2. Load QTM File ---> .qtm format
    Click File --> Open --> Select .qtm file
3. Get this file and the local_zmq_async_client files ready
    At this point you can run the client file should be fine,
4. Run This File
5. Once the connection is established showing:
    'qtm - INFO - Connected' --> Means the python code has connected to QTM, won't start until the .qtm file is ran in QTM
6. In QTM, the .qtm file must be ran using the 'Real-Time Output'
    Click --> 'PLay' on the tool bar
    Look for and Click --> 'Play with Real-Time Output' This will mimic real-time output so the file will run and the python code will capture the data
7. The files should all be running at this point
    async_stream_marker_zmq_unity --> display marker labels, can add LOG option to show each marker data per frame, sending the data async
    local_zmq_async_client --> display the data being captured from the zmq server
    """


import asyncio
import argparse


import qtm
from qtm.packet import QRTComponentType
from qtm import QRTEvent as event
import xml.etree.ElementTree as ET

import logging
from datetime import datetime
import pandas as pd

import math


import zmq
from zmq.asyncio import Context
from struct import *

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("async_stream_marker_zmq_unity")
frame_num_list = list()
marker_data_master_list = list()  # contiains all the values for each marker at each frame, a row/frame is appended at a time

"""ZMQ Setup For Server"""
addr = "tcp://127.0.0.1:7555" # address and port for the server
context = zmq.Context()
push = context.socket(zmq.PUSH) # create socket using ZMQ PUSH for Async, client will have PULL
push.bind(addr) # bind the socket to the add and port


def get_user_input():
    """
    Get users input for the filename that will be saved
    :return: Users inputted file name with data
    """
    task_type = input("Enter type of Exercise:")
    subject_num = input("Enter Subject Number: ")
    level = input("Height of Placement Table: ")
    interval = input("Enter Interval Duration: ")
    weight = input("Weight of Load: ")
    today = datetime.today()
    month = today.month
    day = today.day
    year = today.year
    return f"{task_type}_{subject_num}_{weight}_{interval}_{level}_{month}-{day}-{year}"


def save_xml_file(xml_string, filename):
    """ XML String object obtained from QTM and saved to be used for getting information about the 3D parameters used in QTM

    :param xml_string: A element tree type object containg the xml contents from QTM
    :param filename:   String for file name obtained from user input
    :return:        The xml is returned
    """
    LOG.info("Getting XML 3D parameters")
    LOG.info("Saving XML 3D file")
    tree = ET.ElementTree()  # Create empty object of type ElementTree for xml format
    xml = ET.fromstring(xml_string)  # store xml captured from QTM
    tree._setroot(xml)  # Use previous object to insert xml as root in the tree
    xml_filename = "3D_" + filename  # filename = get_user_input()   # string for the xml filename that will be obtained from user input
    tree.write(xml_filename + ".xml")  # xml_filename = "3D_" + filename # write will write the file out as an .xml.

    return xml


def get_marker_labels(xml):
    """
        Obtain marker names from the XML captured from QTM
    :param xml: The xml iterator object containing the contents of the xml obtained from QTM
    :return: A list of the marker names
    """
    LOG.info("Getting Marker Labels")
    markers_from_xml = list()  # list that will contain the marker names
    markers = xml.findall("*/Label/Name")  # xml iterator object
    for marker in markers:  # loop to iterate through xml
        markers_from_xml.append(marker.text.strip())  # marker names appended

    return markers_from_xml  # return list of the marker names


def create_labels_for_multindex_column_levels(marker_labels_lst):
    """
            Create the lists for columns using marker names
    :param marker_labels_lst:  The list containing the marker names
    :type marker_labels_lst: list
    :return: two list of strings repreenting the header columns for each marker that will be used to create the multiindex dataframe
    """
    marker_duplicate_labels = list()  # list that will contain the marker names duplicated for the use of creating columns for multindex/ sub sections
    marker_labels_xyz = list()  # list that will contain the marker names appended with X, Y , and Z for each marker name
    for marker in marker_labels_lst:  # loop to iterate marker names to create list of names
        label = marker.strip()
        marker_duplicate_labels.extend(label for _ in range(3))  # add the duplict jobs for the marker labels
        label_xyz = ((label + ' X'), (label + ' Y'), (label + ' Z'))  # string marker label for each direction
        marker_labels_xyz.extend(label_xyz)

    return marker_duplicate_labels, marker_labels_xyz

async def sender(my_string=",".join(map(str, [0] * 117))):
    """

    :param my_string: string containing the marker data sepearated by columns
    :return: sending marker data per frame to client
    """

    length = len(my_string.encode()) # get length/size of bytes of encoded string
    pack_my_string = pack(f'<{length}s', my_string.encode()) # must pack the bytes using struct before sending the data out to client. packed using < little endian for python, 's' for string
    push.send_multipart([pack_my_string]) # send the packed bytes to the client


async def packet_receiver(queue, filename, marker_labels):
    """ Asynchronous function that processes queue until None is posted in queue """
    LOG.info("Entering packet_receiver")
    while True:
        packet = await queue.get()
        if packet is None:
            break

        file = filename + ".txt"
        f = open(file, 'a+')
        marker_data_per_frame = list()  # will keep temporary storage of marker data for every frame which will be appended to master list making it a row in the list

        if QRTComponentType.Component3d in packet.components:  # if packet contains a 3D

            """EACH PACKET COMPONENT HAS A:
                Framenumber
                Header and Markers"""

            framenumber = packet.framenumber  # framenumber obtain for every packet
            # LOG.info(framenumber)
            frame_num_list.append(framenumber)
            header, markers = packet.get_3d_markers()  # header and markers are a struct type object
            # LOG.info(header)
            # head = "Component info: {}".format(header)
            # LOG.info(head)
            # f.write(str(framenumber) + "\n " + str(head) + "\n")
            # Each component has a HEADER and MARKERS
            for i, marker in enumerate(markers):
                marker_label = marker_labels[i]
                """Each marker is structured like this
                RT3DMarkerPosition = namedtuple("RT3DMarkerPosition", "x y z")"""
                xyz = f"(x={marker.x:.3f}, y={marker.y:.3f}, z={marker.z:.3f})\n"
                marker_str = "\t " + marker_labels[i] + ": " + xyz
                # LOG.info(marker_str)
                # f.write(marker_str)

                x = marker.x  # x value of marker
                y = marker.y  # y value of marker
                z = marker.z  # z value of marker

                if (math.isnan(x)):  # if there is a value that is a nan value which is just 0
                    LOG.info(f'ZEROO IN MARKER {marker_str}')
                    x = 0.0
                    y = 0.0
                    z = 0.0

                marker_data_per_frame.append(round(x, 3))  # append x value to row rounding to 3 decimal points
                marker_data_per_frame.append(round(y, 3))  # append y value to row rounding to 3 decimal points
                marker_data_per_frame.append(round(z, 3))  # append z value to row rounding to 3 decimal points

                if i == (len(markers) - 1):  # last marker, at this point all the values should be appended to list
                    marker_data_master_list.append(marker_data_per_frame)  # append to master list, the list created will be appended to the bigger data list containing all the marker data for each fram
                    marker_data_per_frame_str = ','.join(map(str, marker_data_per_frame))
                    await sender(marker_data_per_frame_str)
        else:
            f.close()
    LOG.info("Exiting packet_receiver")


async def main(interface=None):
    """ Main function """

    qtm_ip = '127.0.0.1'  # 'await choose_qtm_instance(interface)
    if qtm_ip is None:
        return

    while True:

        connection = await qtm.connect(qtm_ip, 22223, version="1.19", timeout=None)

        if connection is None:
            return connection

        while connection:

            # filename = get_user_input()  # use user input for creating filename enter
            filename = "stream_markers"
            await connection.await_event(event.EventRTfromFileStarted, timeout=None) # event notice when file has started
            xml_string = await connection.get_parameters(parameters=["3d"]) # request and get xml of the 3D parameters from QTM
            xml = save_xml_file(xml_string, filename) # parse the data collected and save into .xml file, obtain the xml
            LOG.info("XML Saved")
            marker_labels = get_marker_labels(xml) # using xml which contains the marker names parse the file to get only the names
            print("Marker Labels: ", marker_labels)

            # LOG.info("Waiting for Capture to Start")
            # LOG.info("Capture Started")
            queue = asyncio.Queue() # asyncio queue

            asyncio.ensure_future(packet_receiver(queue, filename, marker_labels)) # add async function packet_receiver to the asyncio loop event

            try:
                await connection.stream_frames(components=["3d"], on_packet=queue.put_nowait) # request and get packet with frames containing only 3D data from QTM, adding to queue
            except qtm.QRTCommandException as exception:
                LOG.info("exception %s", exception)

            await asyncio.sleep(1.0) # sleep 1sec

            await connection.await_event(event.EventRTfromFileStopped, timeout=None)  # event notice when file is stopped
            # connection = None
            #
            # await connection.stop()
            # await connection.close()

            ######################## MOCAP DF ################################################################
            marker_duplicate_labels, marker_labels_xyz = create_labels_for_multindex_column_levels(marker_labels)

            # Construct array out of the two list labels to corresponding xyz label
            # I want to create multiindex so according the the 2nd link a double list should be used
            # so that they can be combined into tuples (i.e HeadF has three different 'sections' Head F X/Y/Z.
            # In other words, HeadF will have three pairs; (HeadF, HeadF X), (HeadF, HeadF Y), (HeadF, HeadF Z)
            marker_labels_arrays = [marker_duplicate_labels, marker_labels_xyz]
            # LOG.info(body_to_index_labels)
            # Form tuple with corresponding labels
            marker_label_tuples = list(zip(*marker_labels_arrays))
            # Now create teh MultiIndex varible that will be used as the index for the columns
            # There will be 1 header column with 3 sub-header column.
            index = pd.MultiIndex.from_tuples(marker_label_tuples, names=['Marker Names', 'Framenumber'])

            df = pd.DataFrame(marker_data_master_list, index=frame_num_list, columns=index)
            # df.to_csv(filename+".csv", sep=",")
            # print(df)
            ######################## MOCAP DF #############################################################

        # connection.disconnect()


def parse_args():
    parser = argparse.ArgumentParser(description="Example to connect to QTM")
    parser.add_argument(
        "--ip",
        type=str,
        required=False,
        default="127.0.0.1",
        help="IP of interface to search for QTM instances",
    )  # ip has to be my laptop/device

    return parser.parse_args()


if __name__ == "__main__":
    # args = parse_args()
    asyncio.get_event_loop().run_until_complete(main())