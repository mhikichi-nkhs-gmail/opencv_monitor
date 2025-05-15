import socket
import struct
import cv2
import numpy as np
import time
from PIL import ImageFont, ImageDraw, Image


PORT = 12345
HOST = ''  # すべてのインターフェースで受信

def receive_exact(sock, size):
    data = b''
    while len(data) < size:
        more = sock.recv(size - len(data))
        if not more:
            raise EOFError("ソケットが閉じられました")
        data += more
    return data


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"待機中: ポート {PORT}")

    conn, addr = server.accept()
    print(f"接続: {addr}")

    fname_base="img/frame"
    fcnt=0

    sttime=0
    stream=False
    try:
        while True:
            sttime = int(time.time() * 1000)

            # 4バイトの画像サイズ（ネットワークバイトオーダ）
            size_data = receive_exact(conn, 4)
            img_size = struct.unpack('!I', size_data)[0]

            # 画像データ本体
            img_data = receive_exact(conn, img_size)
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is not None:
                edtime = int(time.time() * 1000)
               # print(f"diff: {edtime-sttime}")
                h, w = frame.shape[:2]

                #frame = cv2.resize(frame, (w//2, h//2))
                if stream:
                    cv2.putText(frame, "Image Save...", (20, 50), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255,255,255))
                cv2.imshow("Remote Camera", frame)
                sttime = int(time.time() * 1000)

                if stream:
                    cv2.imwrite(f"{fname_base}{fcnt:04d}.jpg",frame)
                    fcnt+=1                                        

                key= cv2.waitKey(1)
                if key == ord('c'):
                    print("保存しました")
                    cv2.imwrite(f"{fname_base}{fcnt:04d}.jpg",frame)
                    fcnt+=1
                if key == ord('s'):
                    stream = not stream
                    print(stream)

                if key == ord('q'):
                    break
    finally:
        conn.close()
        server.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
