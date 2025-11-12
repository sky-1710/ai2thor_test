import os
os.environ["AI2THOR_OSMESA"] = "1"

import time 
from ai2thor.controller import Controller

# --- [선택] OpenCV 사용 가능하면 실시간 창으로 보기 ---
try:
    import cv2
    USE_CV2 = True
except Exception:
    from PIL import Image
    USE_CV2 = False

def show_third_party(event, index=0, win='third_person'):
    """third-party 카메라 프레임을 화면에 표시"""
    frame = event.third_party_camera_frames[index]
    if USE_CV2:
        import cv2
        cv2.imshow(win, frame[:, :, ::-1])  # RGB->BGR
        cv2.waitKey(1)
    else:
        # PIL fallback (느림, 새 창 반복 생성 주의)
        Image.fromarray(frame).show()

# =========================
# 1) 컨트롤러 & CCTV 카메라
# =========================
controller = Controller(scene="FloorPlan1", width=800, height=600, gridSize=0.25)

# 천장/벽 모서리 느낌의 고정 카메라 (원하면 좌표/각도 바꿔도 됨)
cctv_pos = dict(x=2.0, y=2.5, z=-2.0)   # 천장 근처
cctv_rot = dict(x=45, y=-45, z=0)       # 아래로 45°, 왼쪽 대각
ev = controller.step(action="AddThirdPartyCamera", position=cctv_pos, rotation=cctv_rot)
cam_id = ev.metadata["thirdPartyCameras"][-1]["thirdPartyCameraId"]
show_third_party(ev)

# ================
# 2) 냉장고 열기
# ================
fridge_id = None
for o in ev.metadata["objects"]:
    if o["objectType"] in ["Fridge", "FridgeDoor"] and o.get("openable", False):
        fridge_id = o["objectId"]
        break

if fridge_id:
    ev = controller.step(action="OpenObject", objectId=fridge_id)
    show_third_party(ev)
else:
    print("❌ No openable fridge found.")

# =====================
# 3) Apple ID 확보
# =====================
apple_id = None
for o in ev.metadata["objects"]:
    if o["objectType"] == "Apple":
        apple_id = o["objectId"]
        break

if not apple_id:
    raise RuntimeError("❌ No Apple found in scene.")

# ==============================
# 4) 탐색: Apple이 보일 때까지
# ==============================
# 약간 아래를 보게 하면 가시성↑
ev = controller.step(action="LookDown", degrees=30)
show_third_party(ev)

found = False
# 45도씩 최대 360도 회전, 각 방향에서 최대 5스텝 전진하며 탐색
for _ in range(8):
    for _ in range(5):
        # 현재 가시성 체크
        objs = ev.metadata["objects"]
        apple = next((x for x in objs if x["objectId"] == apple_id), None)
        if apple and apple.get("visible", False):
            print("Apple visible, distance:", apple.get("distance"))
            found = True
            break
        # 한 칸 전진
        ev = controller.step(action="MoveAhead")
        show_third_party(ev)
    if found:
        break
    # 45도 회전
    ev = controller.step(action="RotateRight", degrees=45)
    show_third_party(ev)

# ======================
# 5) 사과 집기 시도
# ======================
if found:
    time.sleep(0.02)
    ev = controller.step(action="PickupObject", objectId=apple_id)
    show_third_party(ev)
    print("Apple picked up:", ev.metadata["lastActionSuccess"])
    print("Held objects:", ev.metadata.get("inventoryObjects", []))
else:
    print("Could not bring Apple into view.")

# 종료 처리 (OpenCV 사용 시 창 유지)
if USE_CV2:
    import cv2
    print("Press any key to exit.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
