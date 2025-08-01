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

# マウスイベントハンドラー用のグローバル変数
mouse_x = 0
mouse_y = 0
mouse_clicked = False
current_frame = None

def put_text_outlined(img, text, pos, font, font_scale, text_color, outline_color, thickness=1, outline_thickness=3):
    """縁取り文字を描画するヘルパー関数"""
    x, y = pos
    # 縁取り（アウトライン）を描画
    cv2.putText(img, text, (x, y), font, font_scale, outline_color, thickness + outline_thickness, cv2.LINE_AA)
    # メインテキストを描画
    cv2.putText(img, text, (x, y), font, font_scale, text_color, thickness, cv2.LINE_AA)

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y, mouse_clicked, current_frame
    
    # 座標を常に更新
    mouse_x, mouse_y = x, y
    
    # クリックイベントの処理
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_clicked = True
        if current_frame is not None:
            # クリックされた位置のピクセル値を取得
            if 0 <= y < current_frame.shape[0] and 0 <= x < current_frame.shape[1]:
                # BGR値を取得
                bgr = current_frame[y, x]
                # HSV値に変換
                hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
                
                print(f"Mouse click at ({x:4d}, {y:4d}):")
                print(f"  BGR: ({bgr[2]:3d}, {bgr[1]:3d}, {bgr[0]:3d})")
                print(f"  HSV: ({hsv[0]:3d}, {hsv[1]:3d}, {hsv[2]:3d})")

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
    
    # 既存のウィンドウを閉じる
    cv2.destroyAllWindows()
    
    # Ctrl+Cシグナルハンドラーを設定
    signal.signal(signal.SIGINT, signal_handler)
    
    # マウスイベントハンドラーを設定
    cv2.namedWindow("Remote Camera")
    cv2.setMouseCallback("Remote Camera", mouse_callback)
    print("Mouse event handler set up")
    
    # 拡大表示モード（1=元サイズ, 2=2倍拡大, 4=4倍拡大）
    scale_factor = 1
    # オーバーレイ表示フラグ
    show_overlay = True

    while not quit_flag:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        server.settimeout(1.0)  # 1秒のタイムアウトを設定
        print(f"待機中: ポート {PORT}")

        try:
            conn, addr = server.accept()
            print(f"接続: {addr}")
        except socket.timeout:
            server.close()
            continue  # タイムアウト時はループを続行
        except Exception as e:
            print(f"ソケットエラー: {e}")
            server.close()
            break

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
                    
                    # オーバーレイ表示用のフレームを作成
                    display_frame = frame.copy()
                    
                    # オーバーレイ表示が有効な場合のみテキストを追加
                    if show_overlay:
                        if scale_factor > 1:
                            # 拡大モード表示（縁取り文字）
                            put_text_outlined(display_frame, f"Scale: {scale_factor}x", (20, 30), 
                                            cv2.FONT_HERSHEY_DUPLEX, 0.7, (0,255,0), (0,0,0), 2, 2)
                        elif scale_factor == 1:
                            # 元サイズ表示時は現在のサイズを表示（縁取り文字・桁揃え）
                            put_text_outlined(display_frame, f"Current: {w:4d}x{h:4d}", (20, 30), 
                                            cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (0,0,0), 2, 2)
                        
                        if stream:
                            put_text_outlined(display_frame, "Image Save...", (20, 50), 
                                            cv2.FONT_HERSHEY_DUPLEX, 0.5, (255,255,255), (0,0,0), 1, 2)
                        
                        # マウス位置のピクセル値を表示
                        if 0 <= mouse_y < display_frame.shape[0] and 0 <= mouse_x < display_frame.shape[1]:
                            bgr = display_frame[mouse_y, mouse_x]
                            hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
                            
                            # ピクセル値表示（画面下部・縁取り文字・桁揃え）
                            info_text = f"({mouse_x:4d},{mouse_y:4d}) BGR:({bgr[2]:3d},{bgr[1]:3d},{bgr[0]:3d}) HSV:({hsv[0]:3d},{hsv[1]:3d},{hsv[2]:3d})"
                            put_text_outlined(display_frame, info_text, (10, display_frame.shape[0] - 20), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), (0,0,0), 1, 2)
                            
                            # マウス位置に十字線を表示
                            cv2.line(display_frame, (mouse_x-10, mouse_y), (mouse_x+10, mouse_y), (0,255,0), 1)
                            cv2.line(display_frame, (mouse_x, mouse_y-10), (mouse_x, mouse_y+10), (0,255,0), 1)
                        else:
                            # マウス位置が画像範囲外の場合の表示（縁取り文字・桁揃え）
                            info_text = f"Mouse: ({mouse_x:4d},{mouse_y:4d}) - Out of bounds"
                            put_text_outlined(display_frame, info_text, (10, display_frame.shape[0] - 20), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), (255,255,255), 1, 2)
                    
                    # グローバル変数に現在のフレームを保存（オーバーレイなし）
                    current_frame = frame.copy()
                    
                    cv2.imshow("Remote Camera", display_frame)
                    sttime = int(time.time() * 1000)

                    if stream:
                        # オーバーレイなしで保存
                        cv2.imwrite(f"{fname_base}{fcnt:04d}.jpg", frame)
                        fcnt+=1                                        

                    key= cv2.waitKey(1)
                    if key == ord('c'):
                        print("保存しました")
                        # オーバーレイなしで保存
                        cv2.imwrite(f"{fname_base}{fcnt:04d}.jpg", frame)
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
                    elif key == ord('o'):
                        # オーバーレイ表示切り替え
                        show_overlay = not show_overlay
                        print(f"Overlay display: {'ON' if show_overlay else 'OFF'}")
                    elif key == ord('t'):
                        # テスト用: 強制的に画像を縮小してから拡大
                        print("テスト: 画像を強制的に縮小してから拡大")
                        frame = cv2.resize(frame, (w//2, h//2))
                        frame = cv2.resize(frame, (w, h))
                        # display_frameも更新してテスト表示
                        display_frame = frame.copy()
                        if show_overlay:
                            put_text_outlined(display_frame, "TEST: Resize down->up", (20, 70), 
                                            cv2.FONT_HERSHEY_DUPLEX, 0.7, (0,0,255), (255,255,255), 2, 2)

                    if key == ord('q'):
                        print("プログラムを終了します...")
                        quit_flag = True
                        break
        except:
            try:
                conn.close()
            except:
                pass
            server.close()
            cv2.destroyAllWindows()
            print("closed")
    
    # プログラム終了時の処理
    try:
        conn.close()
    except:
        pass
    try:
        server.close()
    except:
        pass
    cv2.destroyAllWindows()
    print("プログラムを終了しました")
    sys.exit(0)


if __name__ == "__main__":
    main()
