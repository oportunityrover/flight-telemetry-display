import serial
import asyncio
import websockets
from aiohttp import web

# Serial stuff

# Port Selection
port = '/dev/ttyACM0'
portSelection = input('Use default port: /dev/ttyACM0? Y/n: ')
if portSelection == 'n':
    port = input('Port: ')

baud = 115200
ser = serial.Serial(port, baud, timeout=1)

USERS = set()

async def notify_state(STATE):
    if USERS:  # asyncio.wait doesn't accept an empty list
        message = STATE
        await asyncio.wait([user.send(message) for user in USERS])


async def register(websocket):
    USERS.add(websocket)


async def unregister(websocket):
    USERS.remove(websocket)
    
async def counter(websocket, path):
    await register(websocket)
    try:
        # await websocket.send("HELLO")
        async for message in websocket:
            print(message)
    finally:
        await unregister(websocket)

# Handle income serial data and send to client via websockets
async def serial_stream():
    readCount = 0  # Used to limit the amount of data sent to site
    while True:
        if ser.isOpen():

            # read serial content, strip trailing /r/n, decode bytes to string
            serial_content = ser.readline().strip().decode('utf-8')

            if len(serial_content) and readCount == 9:  # make sure we don't send a blank message (happens) and limits render time
                print(serial_content)  # logging/debugging

                await notify_state("1,1,1,1,1")

                # for some reason including the sleep makes it work on windows, if it causes and issues the sleep
                # time can be decreased
                # please note that it is in seconds, not millisecond
                await asyncio.sleep(0)

                readCount = 0
            readCount += 1
        else:
            # if connection has closed for some reason, try and open it again indefinitely
            # ... objectively a bad idea but hacky solution to allow arduino resets during testing
            # potentially will need to be properly implemented in case connection with rocket is lost and regained mid flight
            ser.open()

start_server = websockets.serve(counter, "localhost", 5678)

#Web server to publish web page contents this includes resources like css and js files
async def index(request):
    return web.FileResponse('../client/index.html')

app = web.Application()
app.add_routes([web.get('/', index)])
app.router.add_static('/', path='../client/')

#https://www.oreilly.com/library/view/daniel-arbuckles-mastering/9781787283695/9633e64b-af31-4adb-b008-972f492701d8.xhtml
asyncio.ensure_future(start_server)
asyncio.ensure_future(serial_stream())
asyncio.ensure_future(web.run_app(app,port=8080)) #Web server running on port 8080


loop = asyncio.get_event_loop()
loop.run_forever()
loop.close()