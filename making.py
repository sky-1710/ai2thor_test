from ai2thor.controller import Controller
from procthor import generate_house  # 예시 함수명

# 1) 컨트롤러 시작
controller = Controller(scene="FloorPlan28", local_build=True)  # 예시 씬 이름

# 2) ProcTHOR으로 교실 스펙 생성
spec = {
    "room_type": "classroom",
    "num_desks": 10,
    "num_chairs_per_desk": 1,
    "has_whiteboard": True,
    "lighting": "bright"
}
house_json = generate_house(spec)

# 3) 씬 생성
event = controller.step(action="CreateHouse", house=house_json)
assert event.metadata["last_event"]["success"]

# 4) 초기화 및 테스트
controller.step(action="Initialize", gridSize=0.25)
