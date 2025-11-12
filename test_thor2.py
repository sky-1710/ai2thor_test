
import ai2thor
from ai2thor.controller import Controller
controller = ai2thor.controller.Controller(agentMode="arm",
scene="FloorPlan203",
visibilityDistance=1.5,
gridSize=0.5,
renderDepthImage=False,
renderInstanceSegmentation=False,
width=800, height=600,
fieldOfView=60)



