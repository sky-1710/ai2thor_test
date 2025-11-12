import os
os.environ["AI2THOR_OSMESA"] = "1"

from ai2thor.controller import Controller
import time

controller = Controller(
    scene="FloorPlan1",
    width=800, height=600,
    server_timeout=120
)


event = controller.step(action="Pass")  

print("inital position:", event.metadata["agent"]["position"])
print("rotation:", event.metadata["agent"]["rotation"])

event = controller.step(action="MoveAhead")
print("position:", event.metadata["agent"]["position"])


event = controller.step(action="RotateLeft")
print("rotation:", event.metadata["agent"]["rotation"])


for _ in range(2):
    event = controller.step(action="RotateRight")
    time.sleep(0.5)

for _ in range(4):
    event = controller.step(action="MoveAhead")
    time.sleep(0.5)

print("final position:", event.metadata["agent"]["rotation"])
