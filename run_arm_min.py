# run_arm_min.py
import os
from ai2thor.controller import Controller

USE_HEADLESS = False  # True면 창 없이(OSMesa), False면 WSLg 창

if USE_HEADLESS:
    os.environ["AI2THOR_OSMESA"] = "1"
    os.environ.pop("DISPLAY", None)
else:
    os.environ.pop("AI2THOR_OSMESA", None)
    os.environ.setdefault("DISPLAY", ":0")

# 핵심: agentMode는 **kwargs(unity_initialization_parameters)**로 전달
c = Controller(
    scene="FloorPlan1_physics",
    width=800, height=600,
    # ↓↓↓ 이게 포인트
    agentMode="arm",          # mid-level 팔 제어 활성화 (agentControllerType 필요 없음)
)

print("Scene:", c.last_event.metadata["sceneName"])

# 간단 동작 테스트 (mid-level 액션)
c.step(
    action="MoveMidLevelArm",
    position=dict(x=0.01, y=0.0, z=0.01),
    speed=2, returnToStart=False, handCameraSpace=False
)
c.step(action="MoveArmBase", y=0.9, speed=2, returnToStart=False)
