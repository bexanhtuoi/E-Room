import subprocess
import sys

sys.path.insert(0, "C:/Users/PC/Downloads/E-Room/backend")

from sqlmodel import Session, text

from app.database import engine

REPO = "C:/Users/PC/Downloads/E-Room"


def sh(cmd):
    out = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=REPO)
    return out.stdout.strip()


def room_ids():
    return [r for r in sys.argv[1].split(",") if r.strip()]


def main():
    for room_id in room_ids():
        print(f"=== room {room_id} ===")

        with Session(engine) as db:
            room = db.exec(text(f"SELECT status,enable_transcript,max_participants FROM rooms WHERE id={room_id}")).all()
            print("db:", room)

            msgs = db.exec(
                text(f"SELECT COUNT(*), SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) FROM messages WHERE room_id={room_id}")
            ).all()
            print("messages total/tester:", msgs)

            scores = db.exec(text(f"SELECT COUNT(*), COALESCE(AVG(overall), 0) FROM pronunciation_scores WHERE room_id={room_id}")).all()
            print("scores count/avg:", scores)

        print("presence:", sh(f"docker exec redis redis-cli SCARD room:{room_id}:participants"))
        print("transcriber_lock_ttl:", sh(f"docker exec redis redis-cli TTL room:{room_id}:transcriber_running"))

        logs = sh("docker logs ai-transcriber --since 30m")
        print("transcriber_log_lines:", sum(1 for line in logs.splitlines() if str(room_id) in line))

        try:
            users = sh(f"docker exec ai-transcriber ls /app/log/speech/room_{room_id}/").split()
            print("speech_files:", users)
        except Exception as error:
            print("speech_files: ?", str(error)[:80])

        try:
            sys.path.insert(0, "C:/Users/PC/Downloads/E-Room/backend")
            from app.integration.minio import get_minio_client

            client = get_minio_client()
            objs = list(client.list_objects("eroom", prefix=f"speech/room_{room_id}/", recursive=True))
            print("minio_objects:", len(objs))
        except Exception as error:
            print("minio_objects: ?", str(error)[:80])


if __name__ == "__main__":
    main()
