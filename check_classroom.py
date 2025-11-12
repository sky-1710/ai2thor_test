from ai2thor.controller import Controller
from ai2thor import wsgi_server

EXEC = r"/mnt/c/Users/Owner/blog/ai2thor_local/unity/builds/thor-Linux64.x86_64"   # 또는 /mnt/c/.../AI2THOR.x86_64

c = Controller(
    local_executable_path=EXEC,  # ← 커스텀 빌드 강제 사용
    width=800, height=600,
    server_timeout=120, server_start_timeout=300,  # 시작 대기 여유
    host="127.0.0.1",  # 로컬
    # Windows면 기본이 WSGI라 별도 지정 불필요하지만, 명시하려면 ↓
    server_class=wsgi_server.WsgiServer
)
print("scenes_in_build sample:", list(sorted(c.scenes_in_build))[:8])
c.reset("classroom_scene")
