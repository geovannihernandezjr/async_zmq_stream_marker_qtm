# async_zmq_stream_marker_qtm
created to stream mocap data from Qualisys Tracking Manager (QTM) to client using PYTHON in asynchronous manner.
Using QTM python sdk to obtain the data in real-time and be able to transmit that to another client

python version >= 3.7
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
    
    
Use the requirements.txt to install the packages needed to execute the code
pip install -r requirements.txt
