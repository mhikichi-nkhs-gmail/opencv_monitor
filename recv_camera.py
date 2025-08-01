import socket
import struct
import cv2
import numpy as np
import time
import sys
import signal
from PIL import ImageFont, ImageDraw, Image


PORT = 12345
HOST = ''  # すべてのインターフェースで受信

# グローバル終了フラグ
quit_flag = False

def signal_handler(sig, frame):
    global quit_flag
    print("\nCtrl+C detected. Exiting...")
    quit_flag = True

def receive_exact(sock, size):
    data = b''
    while len(data) < size:
        more = sock.recv(size - len(data))
        if not more:
            raise EOFError("ソケットが閉じられました")
        data += more
    return data


def main():
    global quit_flag
    
    # Ctrl+Cシグナルハンドラーを設定
    signal.signal(signal.SIGINT, signal_handler)
    
    # 拡大表示モード（1=元サイズ, 2=2倍拡大, 4=4倍拡大）
    scale_factor = 1

    while not quit_flag:
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
            while not quit_flag:
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

                   # frame = cv2.resize(frame, (w//2, h//2))
                    
                    # 拡大表示処理: 受信した画像サイズに対して倍率を適用
                    if scale_factor > 1:
                        # 受信した画像サイズに対して倍率を適用
                        target_width = w * scale_factor
                        target_height = h * scale_factor
                        
                        # 画像を拡大
                        frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
                        # 拡大モード表示
                        cv2.putText(frame, f"Scale: {scale_factor}x", (20, 30), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0,255,0), 2)
                    elif scale_factor == 1:
                        # 元サイズ表示時は現在のサイズを表示
                        cv2.putText(frame, f"Current: {w}x{h}", (20, 30), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), 2)
                    
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
                    
                    # 拡大表示モード切り替え
                    if key == ord('1'):
                        scale_factor = 1
                        print("モード: 元サイズ表示")
                    elif key == ord('2'):
                        scale_factor = 2
                        print("モード: 2倍拡大表示")
                    elif key == ord('4'):
                        scale_factor = 4
                        print("モード: 4倍拡大表示")
                    elif key == ord('t'):
                        # テスト用: 強制的に画像を縮小してから拡大
                        print("テスト: 画像を強制的に縮小してから拡大")
                        frame = cv2.resize(frame, (w//2, h//2))
                        frame = cv2.resize(frame, (w, h))
                        cv2.putText(frame, "TEST: 縮小→拡大", (20, 70), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0,0,255), 2)

                    if key == ord('q'):
                        print("プログラムを終了します...")
                        quit_flag = True
                        break
        except:
            conn.close()
            server.close()
            cv2.destroyAllWindows()
            print("closed")
    
    # プログラム終了時の処理
    try:
        conn.close()
        server.close()
    except:
        pass
    cv2.destroyAllWindows()
    print("プログラムを終了しました")


if __name__ == "__main__":
    main()
