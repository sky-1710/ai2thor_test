import os, traceback, math, time
os.environ["AI2THOR_OSMESA"] = "1"

from ai2thor.controller import Controller

def try_move_arm(ctrl, coordinate_space="armBase"):
    print(f"\n[TRY] MoveArm in coordinateSpace='{coordinate_space}'")
    evt0 = ctrl.last_event
    arm_meta = evt0.metadata.get("arm", None)
    print("arm metadata keys:", list(arm_meta.keys()) if arm_meta else None)

    # armBase 기준은 초기 팔 위치가 (x=0, y=0, z=0.5) 근처라고 문서에 나와 있음
    if coordinate_space == "armBase":
        pos = dict(x=0.0, y=0.10, z=0.60)
    else:  # world 좌표계: 현재 에이전트 포즈 근처로 살짝
        a = evt0.metadata["agent"]["position"]
        pos = dict(x=a["x"]+0.05, y=a["y"]+0.95, z=a["z"]+0.10)

    evt = ctrl.step(
        action="MoveArm",
        position=pos,
        speed=0.5,
        coordinateSpace=coordinate_space,   # 핵심!
        restrictMovement=False              # 제약 완화해 테스트
    )
    print("MoveArm success?:", evt.metadata.get("lastActionSuccess", False))
    if not evt.metadata.get("lastActionSuccess", False):
        print("lastAction:", evt.metadata.get("lastAction"))
        print("errorMessage:", evt.metadata.get("errorMessage"))
    return evt.metadata.get("lastActionSuccess", False)

def probe_arm_activation():
    ctrl = None
    try:
        ctrl = Controller(
            scene="FloorPlan1_physics",
            agentMode="arm",
            width=640, height=480,
            server_timeout=120,
            renderDepthImage=False,
            renderInstanceSegmentation=False,
            gridSize=0.25, snapToGrid=False
        )

        evt = ctrl.last_event
        print("Agent pos:", evt.metadata["agent"]["position"])
        print("Agent rot:", evt.metadata["agent"]["rotation"])
        print("Has 'arm' in metadata?:", "arm" in evt.metadata)

        # 1) armBase 좌표로 시도
        ok = try_move_arm(ctrl, "armBase")
        # 2) world 좌표로도 시도
        if not ok:
            ok = try_move_arm(ctrl, "world")

        # 3) PickupObject도 arm 모드에서 가능한지(보이는 오브젝트 아무거나)
        if ok:
            apple = next((o for o in ctrl.last_event.metadata["objects"]
                          if o["name"] == "Apple" and o.get("visible", False)), None)
            if apple:
                e2 = ctrl.step(action="PickupObject", objectId=apple["objectId"])
                print("PickupObject success?:", e2.metadata.get("lastActionSuccess", False))
            else:
                print("Apple not visible now; skip pickup test.")
        else:
            print("\n⚠️ MoveArm가 두 좌표계 모두 실패했습니다.")
            print("   → 현재 유니티 빌드/씬에 조작(arm) 기능이 포함되지 않았을 가능성 큼.")
            print("   → ManipulaTHOR 구성(전용 빌드/씬) 또는 패키지/빌드 버전 확인 필요.")

    except Exception:
        traceback.print_exc()
    finally:
        if ctrl: ctrl.stop()

if __name__ == "__main__":
    probe_arm_activation()
