from websock import create_connection
print("state conn")
ws = create_connection("ws://echo.websocket.org/")
# ws = create_connection("ws://localhost:3000/")
print("Sending 'Hello, World'...")
ws.send("Hello, World")
print("Sent")
print("Receiving...")
result =  ws.recv()
print("Received '%s'" % result)

# todo impliment
# ws.close()
