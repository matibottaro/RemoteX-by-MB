import socket
import threading
import json
import ctypes
from ctypes import wintypes
import time
import hashlib
import base64
import struct

# Constantes de Windows API
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04

# Códigos de teclas virtuales
VK_CODES = {
    'enter': 0x0D,
    'space': 0x20,
    'left': 0x25,
    'up': 0x26,
    'right': 0x27,
    'down': 0x28,
    'ctrl': 0x11,
    'alt': 0x12,
    'shift': 0x10,
    'win': 0x5B,
    'tab': 0x09,
    'esc': 0x1B,
    'backspace': 0x08,
    'delete': 0x2E,
    'home': 0x24,
    'end': 0x23,
    'pageup': 0x21,
    'pagedown': 0x22,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'volumeup': 0xAF,
    'volumedown': 0xAE,
    'volumemute': 0xAD,
    'playpause': 0xB3,
    'nexttrack': 0xB0,
    'prevtrack': 0xB1
}

class WindowsRemoteControl:
    def __init__(self):
        # Cargar librerías de Windows
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
    def get_screen_size(self):
        return self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
    
    def get_cursor_pos(self):
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y
    
    def set_cursor_pos(self, x, y):
        self.user32.SetCursorPos(int(x), int(y))
    
    def move_cursor_rel(self, dx, dy):
        x, y = self.get_cursor_pos()
        self.set_cursor_pos(x + dx, y + dy)
    
    def mouse_click(self, button='left'):
        if button == 'left':
            self.user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            time.sleep(0.01)
            self.user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        elif button == 'right':
            self.user32.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            time.sleep(0.01)
            self.user32.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
    
    def scroll(self, direction='up', clicks=3):
        delta = 120 * clicks if direction == 'up' else -120 * clicks
        self.user32.mouse_event(0x0800, 0, 0, delta, 0)  # MOUSEEVENTF_WHEEL
    
    def key_press(self, key):
        if isinstance(key, str):
            if key.lower() in VK_CODES:
                vk_code = VK_CODES[key.lower()]
            else:
                # Para caracteres individuales
                vk_code = ord(key.upper())
        else:
            vk_code = key
            
        self.user32.keybd_event(vk_code, 0, 0, 0)  # Key down
        time.sleep(0.01)
        self.user32.keybd_event(vk_code, 0, 0x0002, 0)  # Key up
    
    def key_combination(self, *keys):
        # Presionar todas las teclas
        vk_codes = []
        for key in keys:
            if key.lower() in VK_CODES:
                vk_code = VK_CODES[key.lower()]
            else:
                vk_code = ord(key.upper())
            vk_codes.append(vk_code)
            self.user32.keybd_event(vk_code, 0, 0, 0)
        
        time.sleep(0.01)
        
        # Soltar todas las teclas (en orden inverso)
        for vk_code in reversed(vk_codes):
            self.user32.keybd_event(vk_code, 0, 0x0002, 0)
    
    def type_text(self, text):
        for char in text:
            if char == ' ':
                self.key_press('space')
            elif char == '\n':
                self.key_press('enter')
            else:
                try:
                    # Intentar con el código virtual primero
                    self.key_press(char)
                except:
                    # Si falla, usar Unicode input
                    self._send_unicode_char(char)
    
    def _send_unicode_char(self, char):
        # Enviar caracter Unicode
        for c in char:
            self.user32.SendInput(1, ctypes.byref(self._create_unicode_input(c)), ctypes.sizeof(wintypes.INPUT))
    
    def _create_unicode_input(self, char):
        # Crear estructura INPUT para Unicode
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
            ]
        
        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("ki", KEYBDINPUT)
            ]
        
        # Key down
        input_down = INPUT()
        input_down.type = 1  # INPUT_KEYBOARD
        input_down.ki.wVk = 0
        input_down.ki.wScan = ord(char)
        input_down.ki.dwFlags = 0x0004  # KEYEVENTF_UNICODE
        input_down.ki.time = 0
        input_down.ki.dwExtraInfo = None
        
        return input_down

class WebSocketServer:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.control = WindowsRemoteControl()
        
    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"🚀 Servidor WebSocket iniciado en {self.host}:{self.port}")
            print(f"📱 Conecta desde tu celular usando la IP: {get_local_ip()}")
            print("⏳ Esperando conexiones...")
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"✅ Cliente conectado desde {addr}")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"❌ Error aceptando conexión: {e}")
                        
        except Exception as e:
            print(f"❌ Error iniciando servidor: {e}")
    
    def handle_client(self, client_socket):
        try:
            # Realizar handshake WebSocket
            if not self.websocket_handshake(client_socket):
                print("❌ Error en handshake WebSocket")
                client_socket.close()
                return
            
            print("✅ Handshake WebSocket completado")
            
            while self.running:
                try:
                    # Recibir frame WebSocket
                    message = self.receive_websocket_frame(client_socket)
                    if message is None:
                        break
                    
                    if message:
                        try:
                            command = json.loads(message)
                            print(f"📨 Comando recibido: {command}")
                            self.execute_command(command)
                            
                            # Enviar respuesta
                            response = json.dumps({"status": "success"})
                            self.send_websocket_frame(client_socket, response)
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Error decodificando JSON: {e}")
                            print(f"⚠️ Mensaje recibido: {repr(message)}")
                        except Exception as e:
                            print(f"⚠️ Error ejecutando comando: {e}")
                            
                except Exception as e:
                    print(f"❌ Error recibiendo mensaje: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Error manejando cliente: {e}")
        finally:
            client_socket.close()
            print("🔌 Cliente desconectado")
    
    def websocket_handshake(self, client_socket):
        try:
            # Recibir solicitud HTTP
            request = client_socket.recv(4096).decode('utf-8')
            
            # Extraer Sec-WebSocket-Key
            lines = request.split('\r\n')
            websocket_key = None
            
            for line in lines:
                if line.startswith('Sec-WebSocket-Key:'):
                    websocket_key = line.split(':', 1)[1].strip()
                    break
            
            if not websocket_key:
                return False
            
            # Generar Sec-WebSocket-Accept
            magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept_key = base64.b64encode(
                hashlib.sha1((websocket_key + magic_string).encode()).digest()
            ).decode()
            
            # Enviar respuesta de handshake
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )
            
            client_socket.send(response.encode())
            return True
            
        except Exception as e:
            print(f"❌ Error en handshake: {e}")
            return False
    
    def receive_websocket_frame(self, client_socket):
        try:
            # Leer los primeros 2 bytes
            header = client_socket.recv(2)
            if len(header) < 2:
                return None
            
            # Extraer información del frame
            first_byte = header[0]
            second_byte = header[1]
            
            fin = (first_byte >> 7) & 1
            opcode = first_byte & 0x0f
            masked = (second_byte >> 7) & 1
            payload_length = second_byte & 0x7f
            
            # Leer longitud extendida si es necesario
            if payload_length == 126:
                length_data = client_socket.recv(2)
                payload_length = struct.unpack('>H', length_data)[0]
            elif payload_length == 127:
                length_data = client_socket.recv(8)
                payload_length = struct.unpack('>Q', length_data)[0]
            
            # Leer máscara si existe
            mask_key = None
            if masked:
                mask_key = client_socket.recv(4)
            
            # Leer payload
            payload = client_socket.recv(payload_length)
            
            # Desenmascarar si es necesario
            if masked and mask_key:
                payload = bytes([payload[i] ^ mask_key[i % 4] for i in range(len(payload))])
            
            # Verificar si es un frame de cierre
            if opcode == 8:  # Close frame
                return None
            
            return payload.decode('utf-8')
            
        except Exception as e:
            print(f"❌ Error recibiendo frame: {e}")
            return None
    
    def send_websocket_frame(self, client_socket, message):
        try:
            payload = message.encode('utf-8')
            payload_length = len(payload)
            
            # Crear header del frame
            frame = bytearray()
            frame.append(0x81)  # FIN=1, opcode=1 (text)
            
            if payload_length < 126:
                frame.append(payload_length)
            elif payload_length < 65536:
                frame.append(126)
                frame.extend(struct.pack('>H', payload_length))
            else:
                frame.append(127)
                frame.extend(struct.pack('>Q', payload_length))
            
            # Agregar payload
            frame.extend(payload)
            
            client_socket.send(frame)
            
        except Exception as e:
            print(f"❌ Error enviando frame: {e}")
    
    def execute_command(self, command):
        cmd_type = command.get('type')
        
        try:
            if cmd_type == 'mouse_move':
                x = command.get('x', 0)
                y = command.get('y', 0)
                self.control.set_cursor_pos(x, y)
                
            elif cmd_type == 'mouse_move_rel':
                dx = command.get('dx', 0)
                dy = command.get('dy', 0)
                self.control.move_cursor_rel(dx, dy)
                
            elif cmd_type == 'mouse_click':
                button = command.get('button', 'left')
                self.control.mouse_click(button)
                
            elif cmd_type == 'key_press':
                key = command.get('key')
                if key:
                    self.control.key_press(key)
                    
            elif cmd_type == 'key_combination':
                keys = command.get('keys', [])
                if keys:
                    self.control.key_combination(*keys)
                    
            elif cmd_type == 'type_text':
                text = command.get('text', '')
                if text:
                    self.control.type_text(text)
                    
            elif cmd_type == 'scroll':
                direction = command.get('direction', 'up')
                clicks = command.get('clicks', 3)
                self.control.scroll(direction, clicks)
                
            elif cmd_type == 'volume':
                action = command.get('action', 'mute')
                if action == 'up':
                    self.control.key_press('volumeup')
                elif action == 'down':
                    self.control.key_press('volumedown')
                elif action == 'mute':
                    self.control.key_press('volumemute')
                    
            elif cmd_type == 'media':
                action = command.get('action', 'playpause')
                if action == 'playpause':
                    self.control.key_press('playpause')
                elif action == 'next':
                    self.control.key_press('nexttrack')
                elif action == 'prev':
                    self.control.key_press('prevtrack')
                    
            elif cmd_type == 'shutdown':
                action = command.get('action', 'shutdown')
                import os
                if action == 'shutdown':
                    os.system('shutdown /s /t 5')
                elif action == 'restart':
                    os.system('shutdown /r /t 5')
                elif action == 'sleep':
                    os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                    
        except Exception as e:
            print(f"⚠️ Error ejecutando comando {cmd_type}: {e}")
    
    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == "__main__":
    print("🖥️ Control Remoto PC - Servidor WebSocket Windows")
    print("=" * 50)
    
    local_ip = get_local_ip()
    print(f"🌐 Tu IP local es: {local_ip}")
    print(f"🔧 Puerto: 8888")
    print("📱 Usa esta información en la app móvil")
    print("=" * 50)
    
    server = WebSocketServer()
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Cerrando servidor...")
        server.stop_server()
        print("✅ Servidor cerrado correctamente")