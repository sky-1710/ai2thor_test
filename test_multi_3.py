# test_multi_place_apple_with_cctv.py
import os
os.environ["AI2THOR_OSMESA"] = "1"  # 유니티 창은 안 뜨지만, OpenCV 창은 GUI 백엔드가 있으면 뜸

from ai2thor.controller import Controller
import math
import time

import cv2
import numpy as np

# === 설정 ===
SCENE = "classroom_scene"
APPLE_ID = "Apple|+07.00|+00.64|+03.57"
DESK_ID  = "Desk|+07.11|+00.00|+03.85"

# 로컬 빌드 실행 파일 경로 (반드시 맞게 지정)
EXEC = r"/mnt/c/Users/Owner/blog/ai2thor_local/unity/builds/thor-Linux64.x86_64"

# === CCTV 상태 ===
class CctvState:
    def __init__(self):
        self.yaw = -45.0
        self.pitch = 15.0
        self.follow_agent = 0   # 0번 에이전트를 기본으로 따라감; None이면 고정

cctv = CctvState()

# === 유틸 ===
def get_obj_by_exact_or_prefix(ev, exact_id, prefix_name):
    for o in ev.metadata["objects"]:
        if o["objectId"] == exact_id:
            return o
    for o in ev.metadata["objects"]:
        if o["objectId"].startswith(prefix_name):
            return o
    return None

def nearest_reachable_point(c: Controller, agent_id: int, target_x: float, target_z: float):
    """해당 agent의 ReachablePositions 중 (x,z)에 가장 가까운 포인트를 반환"""
    ev = c.step(action="GetReachablePositions", agentId=agent_id, raise_for_failure=True)
    rps = ev.metadata.get("actionReturn") or []
    if not rps:
        cur = c.last_event.metadata["agent"]["position"]
        return {"x": cur["x"], "y": cur["y"], "z": cur["z"]}
    return min(rps, key=lambda p: (p["x"]-target_x)**2 + (p["z"]-target_z)**2)

def teleport_near(c: Controller, agent_id: int, target_x: float, target_z: float,
                  yaw: float = 0.0, horizon: float = 15.0, force=True):
    """(x,z) 근처 reachable 포인트로 TeleportFull (y는 reachable의 y 사용)"""
    rp = nearest_reachable_point(c, agent_id, target_x, target_z)
    ev = c.step(
        action="TeleportFull",
        agentId=agent_id,
        x=float(rp["x"]), y=float(rp["y"]), z=float(rp["z"]),
        rotation=dict(x=0, y=float(yaw), z=0),
        horizon=float(horizon),
        standing=True,
        forceAction=bool(force),
        raise_for_failure=True
    )
    return ev

def ensure_facing_and_visible(c: Controller, agent_id: int, obj, dx=-0.25, dz=-0.25,
                              yaw=0.0, horizon=18.0):
    """대상 주변 reachable 포인트로 이동하고 시선 맞춰 가시 확보"""
    pos = obj["position"]
    teleport_near(c, agent_id, pos["x"] + dx, pos["z"] + dz, yaw=yaw, horizon=horizon)
    c.step(action="RotateLook", agentId=agent_id, rotation=yaw, horizon=horizon, raise_for_failure=True)
    ev = c.step(action="Pass")
    refreshed = next((o for o in ev.metadata["objects"] if o["objectId"] == obj["objectId"]), None)
    return bool(refreshed and refreshed.get("visible", False))

def safe_pickup(c: Controller, agent_id: int, object_id: str):
    # 커스텀 시그니처(forceVisible 없음) 대응
    return c.step(
        action="PickupObject",
        agentId=agent_id,
        objectId=object_id,
        forceAction=True,
        raise_for_failure=True
    )

def drop_now(c: Controller, agent_id: int, horizon=30.0):
    c.step(action="RotateLook", agentId=agent_id, rotation=0.0, horizon=horizon, raise_for_failure=True)
    return c.step(action="DropHeldObject", agentId=agent_id, raise_for_failure=True)

def put_on_receptacle(c, agent_id: int, receptacle_obj, place_stationary=True):
    """
    커스텀 빌드 PutObject 오버로드 대응:
      1) PutObject(String objectId, ...)
         -> objectId = '리셉터클(책상) objectId'
      2) 실패 시 좌표 버전 폴백: PutObject(float x, float y, ...)
    """
    rec_id = receptacle_obj["objectId"]
    rec_pos = receptacle_obj["position"]

    # 1차: 리셉터클 ID로 직접 두기
    try:
        return c.step(
            action="PutObject",
            agentId=agent_id,
            objectId=rec_id,               # receptacleObjectId 아님!
            forceAction=True,
            placeStationary=bool(place_stationary),
            raise_for_failure=True,
        )
    except Exception:
        # 2차: 좌표로 두기 (y는 책상 높이보다 살짝 위)
        y_drop = float(rec_pos["y"]) + 0.08
        try:
            return c.step(
                action="PutObject",
                agentId=agent_id,
                x=float(rec_pos["x"]),
                y=y_drop,
                forceAction=True,
                placeStationary=bool(place_stationary),
                putNearXY=True,
                raise_for_failure=True,
            )
        except Exception:
            # 마지막: placeStationary=False로 느슨하게
            return c.step(
                action="PutObject",
                agentId=agent_id,
                x=float(rec_pos["x"]),
                y=y_drop,
                forceAction=True,
                placeStationary=False,
                putNearXY=True,
                raise_for_failure=True,
            )

def add_cctv(c: Controller,
             pos=dict(x=2.0, y=2.5, z=-2.0),
             rot=dict(x=45.0, y=-45.0, z=0.0)):
    """3rd-party CCTV 카메라 추가하고 id 반환"""
    ev = c.step(action="AddThirdPartyCamera", position=pos, rotation=rot, raise_for_failure=True)
    cam_id = ev.metadata["thirdPartyCameras"][-1]["thirdPartyCameraId"]
    print("CCTV camera added:", cam_id)
    # 첫 프레임 확인
    if ev.third_party_camera_frames:
        frm = ev.third_party_camera_frames[-1]
        print("CCTV frame shape:", getattr(frm, "shape", "n/a"))
    return cam_id

def get_third_party_index(ev, cam_id):
    cams = ev.metadata.get("thirdPartyCameras", [])
    for i, cinfo in enumerate(cams):
        if cinfo.get("thirdPartyCameraId") == cam_id:
            return i
    return None

def follow_agent_camera(controller: Controller, cam_id: int, agent_id: int,
                        offset=(0.0, 1.7, -2.8), yaw=None, pitch=10.0):
    """에이전트 뒤쪽/위쪽에 카메라를 붙여 3인칭 느낌"""
    ev = controller.last_event
    ag = ev.metadata["agents"][agent_id] if "agents" in ev.metadata else ev.metadata["agent"]
    pos = ag["position"]
    rot = ag["rotation"]  # dict(x: pitch, y: yaw, z)
    yaw_agent = rot.get("y", 0.0)

    # 에이전트 yaw 기준으로 offset 회전 (수평면)
    ox, oy, oz = offset
    rad = math.radians(yaw_agent)
    rx = ox * math.cos(rad) - oz * math.sin(rad)
    rz = ox * math.sin(rad) + oz * math.cos(rad)

    cam_pos = dict(x=pos["x"] + rx, y=pos["y"] + oy, z=pos["z"] + rz)
    cam_rot = dict(x=float(pitch), y=float(yaw if yaw is not None else yaw_agent), z=0.0)

    controller.step(
        action="UpdateThirdPartyCamera",
        thirdPartyCameraId=cam_id,
        position=cam_pos,
        rotation=cam_rot,
        raise_for_failure=True
    )

def cctv_show(ev, controller: Controller, cam_id: int) -> bool:
    """
    마지막 이벤트(ev) 기준으로 CCTV 한 프레임을 OpenCV 창에 표시하고
    키 입력을 처리한다. 계속 진행하려면 True, ESC로 종료하면 False 반환.
    """
    # follow 모드면 카메라 위치 갱신
    if cctv.follow_agent is not None:
        follow_agent_camera(controller, cam_id, cctv.follow_agent,
                            offset=(0.0, 1.7, -2.8), yaw=None, pitch=cctv.pitch)
        ev = controller.step(action="Pass")  # 업데이트 반영

    idx = get_third_party_index(ev, cam_id)
    if idx is not None and ev.third_party_camera_frames:
        frame_rgb = ev.third_party_camera_frames[idx]  # HxWx3 RGB
        frame_bgr = frame_rgb[:, :, ::-1]
        cv2.imshow("CCTV", frame_bgr)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        return False
    elif key in (ord('f'), ord('F')):
        cctv.follow_agent = (0 if cctv.follow_agent is None else None)
        print("Follow mode:", "ON(agent 0)" if cctv.follow_agent is not None else "OFF")
    elif key == ord('r') and cctv.follow_agent is None:
        cctv.yaw -= 5.0
        controller.step(action="UpdateThirdPartyCamera",
                        thirdPartyCameraId=cam_id,
                        rotation=dict(x=cctv.pitch, y=cctv.yaw, z=0.0),
                        raise_for_failure=True)
    elif key == ord('t') and cctv.follow_agent is None:
        cctv.yaw += 5.0
        controller.step(action="UpdateThirdPartyCamera",
                        thirdPartyCameraId=cam_id,
                        rotation=dict(x=cctv.pitch, y=cctv.yaw, z=0.0),
                        raise_for_failure=True)
    return True

def main():
    # 로컬 빌드 강제 사용
    c = Controller(
        local_executable_path=EXEC,
        width=800, height=600,
        server_timeout=120, server_start_timeout=300
    )

    # 에이전트 2명으로 초기화
    c.reset(
        SCENE,
        agentCount=2,
        gridSize=0.25,
        snapToGrid=True
    )
    ev = c.step(action="Pass")

    # CCTV 카메라 1대 추가 (원하면 위치/각도 바꿔도 됨)
    cam_id = add_cctv(c)
    # 초기 프레임 한 번 표시
    if not cctv_show(ev, c, cam_id):
        cv2.destroyAllWindows()
        return

    # 객체 확인
    desk = get_obj_by_exact_or_prefix(ev, DESK_ID, "Desk|")
    apple = get_obj_by_exact_or_prefix(ev, APPLE_ID, "Apple|")
    if desk is None or apple is None:
        raise RuntimeError("Desk 또는 Apple 객체를 찾지 못했습니다.")
    desk_pos = desk["position"]
    print(f"[Resolved] Desk: {desk['objectId']} @ {desk_pos}")
    print(f"[Resolved] Apple: {apple['objectId']} @ {apple['position']}")

    # 초기 위치: 책상 좌/우로 벌리기 (각각 reachable 기반으로 y 자동 결정)
    ev = teleport_near(c, 0, desk_pos["x"] - 0.60, desk_pos["z"] - 0.50, yaw=0.0,   horizon=18.0)
    if not cctv_show(ev, c, cam_id): return
    ev = teleport_near(c, 1, desk_pos["x"] + 0.60, desk_pos["z"] - 0.50, yaw=180.0, horizon=18.0)
    if not cctv_show(ev, c, cam_id): return

    for cycle in range(1, 4):
        print(f"\n=== Cycle {cycle} ===")

        ev = c.step(action="Pass")
        if not cctv_show(ev, c, cam_id): break

        desk  = get_obj_by_exact_or_prefix(ev, desk["objectId"],  "Desk|")
        apple = get_obj_by_exact_or_prefix(ev, apple["objectId"], "Apple|")

        # Agent 0: 사과 집어서 바닥 드롭
        if not ensure_facing_and_visible(c, 0, apple, dx=-0.18, dz=-0.18, yaw=0.0, horizon=16.0):
            ensure_facing_and_visible(c, 0, apple, dx=-0.12, dz=-0.12, yaw=0.0, horizon=12.0)
        ev = c.step(action="Pass");  # 위치조정 후 표시
        if not cctv_show(ev, c, cam_id): break

        safe_pickup(c, 0, apple["objectId"])
        ev = c.step(action="Pass");  # 픽업 직후 표시
        if not cctv_show(ev, c, cam_id): break

        drop_now(c, 0, horizon=30.0)
        ev = c.step(action="Pass")
        if not cctv_show(ev, c, cam_id): break

        # 드롭 후 사과 위치 갱신
        apple = get_obj_by_exact_or_prefix(ev, apple["objectId"], "Apple|")
        floor_pos = apple["position"]

        # Agent 1: 바닥 사과 집어 책상 위로
        ev = teleport_near(c, 1, floor_pos["x"] + 0.25, floor_pos["z"] + 0.25, yaw=180.0, horizon=24.0)
        if not cctv_show(ev, c, cam_id): break
        ensure_facing_and_visible(c, 1, apple, dx=0.10, dz=0.10, yaw=180.0, horizon=20.0)
        ev = c.step(action="Pass")
        if not cctv_show(ev, c, cam_id): break

        safe_pickup(c, 1, apple["objectId"])
        ev = c.step(action="Pass")
        if not cctv_show(ev, c, cam_id): break

        ev = teleport_near(c, 1, desk_pos["x"] + 0.22, desk_pos["z"] - 0.15, yaw=0.0, horizon=6.0)
        if not cctv_show(ev, c, cam_id): break
        put_on_receptacle(c, 1, desk, place_stationary=True)
        ev = c.step(action="Pass")
        if not cctv_show(ev, c, cam_id): break

        # 확인
        apple_check = get_obj_by_exact_or_prefix(ev, apple["objectId"], "Apple|")
        on_desk = apple_check.get("parentReceptacles") and desk["objectId"] in apple_check["parentReceptacles"]
        print("[Check] Apple on desk?", bool(on_desk))

    print("\nDone.")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
