# make_classroom_train00168.py
# pip install --upgrade ai2thor procthor prior pillow

import os, json, copy, math
from ai2thor.controller import Controller
from PIL import Image
import ai2thor, prior
from procthor.scripts.upgrade_house import upgrade_house

os.environ.setdefault("AI2THOR_OSMESA", "1")
print("ai2thor version:", ai2thor.__version__)

# === 1️⃣ 데이터셋 로드 & 업그레이드 ===
ds = prior.load_dataset("procthor-10k")
house = ds["train"][168]
if isinstance(house, (str, bytes)):
    house = json.loads(house)
house = house.get("house", house)

print("original version:", house.get("version", "(unknown)"))
house = upgrade_house(copy.deepcopy(house))
print("upgraded version:", house.get("version", "(unknown)"))

# === 2️⃣ material 필드 호환성 패치 (혹시 남아있는 문자열 머티리얼 대비) ===
def patch_materials(node):
    if isinstance(node, dict):
        for k in list(node.keys()):
            v = node[k]
            if "material" in k.lower():
                if isinstance(v, str):
                    node[k] = {"name": v}
                elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                    node[k] = [{"name": x} for x in v]
                else:
                    patch_materials(v)
            else:
                patch_materials(v)
    elif isinstance(node, list):
        for x in node:
            patch_materials(x)
patch_materials(house)

# === 3️⃣ 컨트롤러 시작 및 하우스 생성 ===
c = Controller(scene="Procedural", width=800, height=600, server_timeout=120)
ev = c.step(action="CreateHouse", house=house)
print("CreateHouse:", ev.metadata.get("lastActionSuccess"), ev.metadata.get("errorMessage"))

if not ev.metadata.get("lastActionSuccess"):
    raise SystemExit("❌ CreateHouse 실패 — 위 에러 메시지 확인")

c.step(action="Initialize", gridSize=0.25)

# === 4️⃣ 교실형 오브젝트 배치 ===
def vec(x=0,y=0,z=0): return {"x":float(x),"y":float(y),"z":float(z)}

sb = ev.metadata["sceneBounds"]
center, size = sb["center"], sb["size"]

rows, cols = 4, 5
spacing_x, spacing_z = 1.2, 1.1
chair_back = -0.45
origin_x = center["x"] - (cols - 1) * spacing_x / 2.0
origin_z = center["z"] - size["z"] * 0.5 + 1.2

for r in range(rows):
    for cidx in range(cols):
        x = origin_x + cidx * spacing_x
        z = origin_z + r * spacing_z
        c.step(action="AddObject", objectType="Desk",  position=vec(x,0.0,z))
        c.step(action="AddObject", objectType="Chair", position=vec(x,0.0,z+chair_back), rotation=vec(0,180,0))

# 교탁/TV(화이트보드 대용)
c.step(action="AddObject", objectType="DiningTable", position=vec(center["x"],0.0,origin_z-0.6))
c.step(action="AddObject", objectType="Television",  position=vec(center["x"],0.9,center["z"]-size["z"]*0.5+0.2))

# === 5️⃣ CCTV 시점 생성 & JPG 저장 ===
def look_at(cam, tgt):
    dx, dy, dz = tgt["x"]-cam["x"], tgt["y"]-cam["y"], tgt["z"]-cam["z"]
    yaw = math.degrees(math.atan2(dx, dz))
    dist = max(1e-6, math.sqrt(dx*dx + dz*dz))
    pitch = -math.degrees(math.atan2(dy, dist))
    return {"x":pitch, "y":yaw, "z":0}

cam_pos = vec(center["x"]-size["x"]*0.45, center["y"]+size["y"]*0.45, center["z"]-size["z"]*0.45)
target  = vec(center["x"], 0.9, origin_z + (rows-1)*spacing_z*0.5)
rot     = look_at(cam_pos, target)

ev = c.step(action="AddThirdPartyCamera", position=cam_pos, rotation=rot, fieldOfView=65)
ev = c.step(action="Pass")
os.makedirs("outputs", exist_ok=True)
Image.fromarray(ev.third_party_camera_frames[0]).save("outputs/train_00168_classroom.jpg", "JPEG")
print("✅ Saved: outputs/train_00168_classroom.jpg")

c.stop()
