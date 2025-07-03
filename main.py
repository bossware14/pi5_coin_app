import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import Image, ImageTk # ต้องติดตั้ง Pillow: pip install Pillow
import io
import time
import threading
import sys # สำคัญ: เพิ่ม import sys
import signal # สำคัญ: เพิ่ม import signal

import RPi.GPIO as GPIO
import time
import threading

# กำหนดโหมดของ GPIO
GPIO.setmode(GPIO.BCM)

# กำหนดขา GPIO
COIN_SENSOR_PIN = 12  # ขาสำหรับตรวจจับการหมุนของเซ็นเซอร์เหรียญ
GPIO_RELAY = 26       # ขาสำหรับควบคุม Relay (เช่น เครื่องจ่ายเหรียญ)

# ตัวแปรสถานะ
coins_to_dispense_target = 0 # จำนวนเหรียญที่ต้องการให้จ่าย (เป้าหมาย)
coins_dispensed_count = 0    # จำนวนเหรียญที่ถูกจ่ายออกไปแล้วจริง
is_dispensing_active = False # สถานะว่ากำลังอยู่ในกระบวนการจ่ายเหรียญหรือไม่

# กำหนด Relay เป็น Active Low หรือ Active High
# ถ้า Relay ทำงานเมื่อขาเป็น LOW ให้ใช้ GPIO.LOW เป็น ON_STATE และ GPIO.HIGH เป็น OFF_STATE
# ถ้า Relay ทำงานเมื่อขาเป็น HIGH ให้ใช้ GPIO.HIGH เป็น ON_STATE และ GPIO.LOW เป็น OFF_STATE
RELAY_ON_STATE = GPIO.LOW  # สมมติว่า Relay ของคุณเป็น Active Low
RELAY_OFF_STATE = GPIO.HIGH

# ฟังก์ชันสำหรับควบคุม Relay
def set_relay_state(state):
    GPIO.output(GPIO_RELAY, state)
    print(f"Relay state set to: {'ON' if state == RELAY_ON_STATE else 'OFF'}")

# ฟังก์ชัน Callback เมื่อเซ็นเซอร์เหรียญตรวจจับการหมุน
def coin_sensor_callback(channel):
    global coins_dispensed_count, is_dispensing_active

    current_state = GPIO.input(channel)
    print(current_state)
    # ตรวจจับขอบขาลง (HIGH to LOW) ซึ่งมักจะบ่งบอกถึงการนับเหรียญ
    # หรือปรับตามลักษณะการทำงานของเซ็นเซอร์คุณ (RISING/FALLING/BOTH)
    if current_state  and is_dispensing_active:
        coins_dispensed_count += 1
        print(f"ตรวจจับเหรียญที่จ่ายออก: {coins_dispensed_count} / {coins_to_dispense_target}")
        if coins_dispensed_count >= coins_to_dispense_target:
            # ถ้าจ่ายครบจำนวนที่ต้องการแล้ว ให้หยุด Relay
            print("จ่ายเหรียญครบแล้ว หยุดการทำงานของ Relay")
            is_dispensing_active = False
            set_relay_state(RELAY_OFF_STATE) # ปิด Relay

# ฟังก์ชันสำหรับเริ่มกระบวนการจ่ายเหรียญ
def start_dispensing(num_coins):
    global coins_to_dispense_target, coins_dispensed_count, is_dispensing_active

    if is_dispensing_active:
        print("กำลังจ่ายเหรียญอยู่ โปรดรอให้เสร็จสิ้น")
        return

    print(f"เริ่มจ่ายเหรียญจำนวน {num_coins} เหรียญ...")
    coins_to_dispense_target = num_coins
    coins_dispensed_count = 0
    is_dispensing_active = True
    set_relay_state(RELAY_ON_STATE) # เปิด Relay เพื่อเริ่มจ่ายเหรียญ


# ตั้งค่าขา Relay เป็น Output และเริ่มต้นด้วยการปิด Relay ไว้
GPIO.setup(GPIO_RELAY, GPIO.OUT, initial=RELAY_OFF_STATE)
print("ตั้งค่า Relay พร้อมใช้งาน")
# ตั้งค่าขา COIN_SENSOR_PIN เป็น Input พร้อม Pull-up
GPIO.setup(COIN_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    # เพิ่ม event detection สำหรับขา COIN_SENSOR_PIN
    # ตรวจจับการเปลี่ยนแปลงสถานะทั้งคู่ (BOTH) 
    # FALLING/RISING ตามลักษณะเซ็นเซอร์
GPIO.add_event_detect(COIN_SENSOR_PIN, GPIO.RISING, callback=coin_sensor_callback, bouncetime=20) # Bouncetime เพิ่มขึ้นเล็กน้อยเพื่อความเสถียร
print(f"รอการเปลี่ยนแปลงสถานะบน GPIO {COIN_SENSOR_PIN} (เซ็นเซอร์เหรียญ)...")
print("กด Ctrl+C เพื่อออก หรือเรียก start_dispensing(จำนวนเหรียญ) เพื่อเริ่มจ่าย")
    # ตัวอย่างการใช้งาน: สั่งจ่ายเหรียญ 2 เหรียญ
    # คุณสามารถเรียกฟังก์ชันนี้จากส่วนอื่นของโปรแกรมของคุณได้ เช่น จาก API call หรือปุ่มกด
    #time.sleep(2) # รอสักครู่ก่อนเริ่ม
    #start_dispensing(2) # สั่งจ่าย 2 เหรียญ
    # ทำให้โปรแกรมทำงานไปเรื่อยๆ เพื่อรอ event และการควบคุม
    #while True:
    #    time.sleep(0.1) # หน่วงเวลาเล็กน้อยเพื่อไม่ให้ CPU ทำงานหนักเกินไป

    # ทำความสะอาด GPIO เมื่อโปรแกรมหยุด


class MoneyExchangeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("เครื่องแลกเงิน")
        
        # --- การตั้งค่า Full Screen และการจัดการขนาดหน้าต่าง ---
        self.geometry("800x480") 
        self.attributes('-fullscreen', True) # ยกเลิกคอมเมนต์เมื่อรันบนอุปกรณ์จริง
        #self.overrideredirect(True) # ยกเลิกคอมเมนต์ถ้าต้องการ Fullscreen แบบไม่มีขอบ/Title Bar เลย (ต้องมีปุ่มปิดแอปเอง)

        # กำหนดให้หน้าต่างหลักสามารถขยายได้
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.selected_amount = 0

        self.qr_countdown_id = None
        self.timeout_screen_id = None

        # --- การกำหนด Style สำหรับ ttk Widgets ---
        self.style = ttk.Style(self)
        # ลองใช้ theme ที่มีอยู่ เช่น 'clam', 'alt', 'default', 'classic'
        self.style.theme_use('clam') 
        
        # กำหนด Style ทั่วไปสำหรับปุ่ม
        self.style.configure('TButton', 
                             font=('Arial', 24, 'bold'), # ขนาด Font เริ่มต้นสำหรับปุ่ม
                             padding=20, # Padding ภายในปุ่ม
                             background='#4CAF50', # สีพื้นหลังปุ่ม
                             foreground='white', # สีตัวอักษร
                             relief='flat' # ลักษณะขอบปุ่ม
                            )
        self.style.map('TButton', 
                       background=[('active', '#45a049')], # สีเมื่อเมาส์ชี้
                       foreground=[('disabled', 'grey')] # สีเมื่อปุ่มถูกปิดใช้งาน
                      )
        
        # กำหนด Style สำหรับ Label ใหญ่ๆ (เช่น Header, ข้อความยืนยัน, หมดเวลา)
        self.style.configure('Header.TLabel', 
                             font=('Arial', 32, 'bold'), # ขนาด Font ใหญ่ขึ้น
                             foreground='#333333', # สีตัวอักษรเข้มขึ้น
                             padding=20 # เพิ่ม padding
                            )
        
        # กำหนด Style สำหรับ Label ข้อความปกติ
        self.style.configure('Info.TLabel', 
                             font=('Arial', 20, 'bold'),
                             foreground='#555555'
                            )
        
        # กำหนด Style สำหรับ Label นับถอยหลัง (สีแดง)
        self.style.configure('Countdown.TLabel',
                             font=('Arial', 28, 'bold'),
                             foreground='red'
                            )
        
        # กำหนด Style สำหรับ Label แสดงข้อผิดพลาด QR Code
        self.style.configure('Error.TLabel',
                             font=('Arial', 28, 'bold'),
                             foreground='darkred'
                            )
        
        # สไตล์สำหรับปุ่มย้อนกลับ/ปิดแอป (เพิ่มเข้ามา)
        self.style.configure('Control.TButton', font=('Arial', 20, 'bold'), 
                             background='#607D8B', foreground='white', relief='flat')
        self.style.map('Control.TButton', 
                       background=[('active', '#546E7A')])


        # สร้าง Frame สำหรับแต่ละหน้าจอ
        # ใช้สีพื้นหลังที่ดูสบายตาขึ้น
        self.main_frame = tk.Frame(self, bg="#E0F2F7") # สีฟ้าอ่อน
        self.confirm_frame = tk.Frame(self, bg="#E0F7FA") # สีฟ้าอ่อนกว่า
        self.qr_frame = tk.Frame(self, bg="#F0F4C3") # สีเขียวอ่อนๆ
        self.timeout_frame = tk.Frame(self, bg="#FFCDD2") # สีแดงอ่อนๆ

        for frame in (self.main_frame, self.confirm_frame, self.qr_frame, self.timeout_frame):
            frame.grid(row=0, column=0, sticky="nsew")

        # เริ่มต้นสร้าง UI ของแต่ละหน้าจอ
        self.init_main_screen()
        self.init_confirm_screen()
        self.init_qr_screen()
        self.init_timeout_screen()

        self.show_frame(self.main_frame)
        
        # ผูก event สำหรับการปรับขนาดหน้าต่างเพื่อให้ grid layout ปรับตาม (สำคัญสำหรับการปรับขนาดอัตโนมัติ)
        self.bind("<Configure>", self.on_resize) 

        # ผูก event สำหรับการปิดหน้าต่าง (เช่น กด X หรือ Alt+F4)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # เพิ่มการจัดการสัญญาณ Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        self.after(100, self.check_signals)


    # --- ส่วนการสร้างหน้าจอต่างๆ ---

    def init_main_screen(self):
        """สร้างหน้าจอหลักสำหรับเลือกจำนวนเงิน"""
        frame = self.main_frame
        frame.grid_columnconfigure(0, weight=1) 
        # เพิ่มแถวสำหรับปุ่มปิด
        for i in range(5): # 0: Label, 1-3: Buttons, 4: Exit Button
            frame.grid_rowconfigure(i, weight=1)
        
        self.info_label = ttk.Label(frame, text="กรุณาเลือกจำนวนเงิน", 
                                    style='Header.TLabel', anchor="center")
        self.info_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        # ฟังก์ชันสำหรับสร้างปุ่มที่เหมือนกัน
        def create_money_button(parent_frame, text, amount, row):
            btn = ttk.Button(parent_frame, text=text, command=lambda: self.show_confirm_screen(amount))
            btn.grid(row=row, column=0, sticky="nsew", padx=80, pady=10) # ลด pady เล็กน้อยเพื่อให้มีที่ว่างสำหรับปุ่มปิด
            return btn

        create_money_button(frame, "20 บาท", 20, 1)
        create_money_button(frame, "50 บาท", 50, 2)
        create_money_button(frame, "100 บาท", 100, 3)

        # --- เพิ่มปุ่มปิดแอป (นี่คือส่วนที่เพิ่มเข้ามา) ---
        btn_exit = ttk.Button(frame, text="ปิดแอป", command=self.on_closing)
        btn_exit.config(style='Control.TButton') # ใช้สไตล์ Control.TButton
        btn_exit.grid(row=4, column=0, sticky="nsew", padx=150, pady=10) # จัดวางที่แถวสุดท้าย
        # --- จบการเพิ่มปุ่มปิดแอป ---

    def init_confirm_screen(self):
        """สร้างหน้าจอยืนยันจำนวนเงิน"""
        frame = self.confirm_frame
        frame.grid_columnconfigure(0, weight=1)
        for i in range(3): 
            frame.grid_rowconfigure(i, weight=1)

        self.confirm_label = ttk.Label(frame, text="คุณเลือกจำนวนเงิน: XX บาท\n\nกดปุ่ม 'ยืนยัน' เพื่อดำเนินการต่อ", 
                                        style='Header.TLabel', justify="center", anchor="center")
        self.confirm_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=40)

        btn_confirm = ttk.Button(frame, text="ยืนยัน", command=lambda: self.start_qr_code_display(self.selected_amount))
        btn_confirm.grid(row=1, column=0, sticky="nsew", padx=150, pady=15)

        btn_back_confirm = ttk.Button(frame, text="ย้อนกลับ", command=lambda: self.show_frame(self.main_frame))
        btn_back_confirm.config(style='Control.TButton') # ใช้สไตล์ Control.TButton
        btn_back_confirm.grid(row=2, column=0, sticky="nsew", padx=200, pady=15)

    def init_qr_screen(self):
        """สร้างหน้าจอแสดง QR Code และเวลานับถอยหลัง"""
        frame = self.qr_frame
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=4) 
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        self.qr_image_label = ttk.Label(frame, text="กำลังโหลด QR Code...", 
                                        style='Info.TLabel', compound="image", anchor="center")
        self.qr_image_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.qr_image_label.bind("<Configure>", self.resize_qr_image)

        self.countdown_label = ttk.Label(frame, text="เวลาที่เหลือ: 30 วินาที", 
                                         style='Countdown.TLabel', anchor="center")
        self.countdown_label.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        btn_back = ttk.Button(frame, text="ย้อนกลับ", command=lambda: self.show_frame(self.main_frame))
        btn_back.config(style='Control.TButton') 
        btn_back.grid(row=2, column=0, sticky="nsew", padx=200, pady=15)

    def init_timeout_screen(self):
        """สร้างหน้าจอแจ้งเตือน 'หมดเวลาทำรายการ'"""
        frame = self.timeout_frame
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        timeout_message_label = ttk.Label(frame, text="หมดเวลาทำรายการ", 
                                          style='Header.TLabel', foreground='red', anchor="center") 
        timeout_message_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=50)

    # --- ส่วนการจัดการการเปลี่ยนหน้าจอและ Logic ---

    def show_frame(self, frame_to_show):
        self._cancel_all_timers()
        
        if frame_to_show == self.main_frame:
            self.qr_image_label.config(image='', text="กำลังโหลด QR Code...")
            self.countdown_label.config(text="เวลาที่เหลือ: 30 วินาที")
            self.current_qr_photo = None
            self.original_qr_image = None

        frame_to_show.tkraise()

    def show_confirm_screen(self, amount):
        self.selected_amount = amount
        self.confirm_label.config(text=f"คุณเลือกจำนวนเงิน: {amount} บาท\n\nกดปุ่ม 'ยืนยัน' เพื่อดำเนินการต่อ")
        self.show_frame(self.confirm_frame)

    def start_qr_code_display(self, amount):
        self.show_frame(self.qr_frame)
        self.qr_image_label.config(text="กำลังโหลด QR Code...", image='')
        
        threading.Thread(target=self._load_qr_code_threaded, args=(amount,)).start()

        self.countdown_time = 30
        self.countdown_label.config(text=f"เวลาที่เหลือ: {self.countdown_time} วินาที")
        self._start_countdown()

    def _start_countdown(self):
        if self.countdown_time > 0:
            self.countdown_time -= 1
            self.countdown_label.config(text=f"เวลาที่เหลือ: {self.countdown_time} วินาที")
            self.qr_countdown_id = self.after(1000, self._start_countdown)
        else:
            self.show_timeout_screen()

    def _load_qr_code_threaded(self, amount):
        data_for_qr = f"Amount:{amount}Baht_Timestamp:{int(time.time())}"
        qr_url = f"https://image-charts.com/chart?chs=150x150&cht=qr&choe=UTF-8&chl={data_for_qr}"
        coin = int(int(amount)/10)
        start_dispensing(coin)
        try:
            response = requests.get(qr_url, timeout=10)
            if response.status_code == 200:
                image_data = io.BytesIO(response.content)
                img = Image.open(image_data)
                self.original_qr_image = img 
                self.after(0, self.resize_qr_image) 
            else:
                self.after(0, lambda: self._handle_qr_error(f"ไม่สามารถดึง QR Code ได้: HTTP {response.status_code}"))
        except requests.exceptions.RequestException as e:
            self.after(0, lambda: self._handle_qr_error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}\nโปรดตรวจสอบอินเทอร์เน็ต"))
        except Exception as e:
            self.after(0, lambda: self._handle_qr_error(f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}"))

    def resize_qr_image(self, event=None):
        if hasattr(self, 'original_qr_image') and self.original_qr_image:
            label_width = self.qr_image_label.winfo_width()
            label_height = self.qr_image_label.winfo_height()
            
            if label_width <= 1 or label_height <= 1: 
                return

            original_width, original_height = self.original_qr_image.size
            
            max_size = 350 
            
            ratio_w = min(label_width / original_width, max_size / original_width)
            ratio_h = min(label_height / original_height, max_size / original_height)
            ratio = min(ratio_w, ratio_h) 
            
            new_width = int(original_width * ratio * 0.9) 
            new_height = int(original_height * ratio * 0.9)

            if new_width > 0 and new_height > 0:
                resized_img = self.original_qr_image.resize((new_width, new_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized_img)
                self.qr_image_label.config(image=photo, text="")
                self.qr_image_label.image = photo 

    def _handle_qr_error(self, message):
        self.qr_image_label.config(text=message, image='', style='Error.TLabel') 
        messagebox.showerror("ข้อผิดพลาด", message)
        self._cancel_all_timers()
        self.show_timeout_screen()

    def show_timeout_screen(self):
        self.show_frame(self.timeout_frame)
        self.timeout_screen_id = self.after(3000, lambda: self.show_frame(self.main_frame))

    def _cancel_all_timers(self):
        if self.qr_countdown_id:
            self.after_cancel(self.qr_countdown_id)
            self.qr_countdown_id = None
        if self.timeout_screen_id:
            self.after_cancel(self.timeout_screen_id)
            self.timeout_screen_id = None

    def on_resize(self, event):
        self.resize_qr_image()

    def on_closing(self):
        """จัดการเมื่อผู้ใช้พยายามปิดหน้าต่าง"""
        if messagebox.askokcancel("ปิดโปรแกรม", "คุณต้องการปิดโปรแกรมหรือไม่?"):
            self.quit_app() # เรียกฟังก์ชันสำหรับปิดโปรแกรมอย่างสะอาด

    # --- เพิ่มฟังก์ชันสำหรับจัดการ SIGINT (Ctrl+C) ---
    def signal_handler(self, sig, frame):
        """
        Handler สำหรับสัญญาณ SIGINT (Ctrl+C)
        จะถูกเรียกเมื่อผู้ใช้กด Ctrl+C ใน Terminal
        """
        print("\nCtrl+C ถูกตรวจพบ ปิดโปรแกรม...")
        self.quit_app()

    def check_signals(self):
        """
        ฟังก์ชันที่ถูกเรียกโดย Tkinter's after method เพื่อตรวจสอบสัญญาณ
        จำเป็นเพราะ Tkinter's mainloop บล็อกสัญญาณโดยตรง
        """
        self.tk.dooneevent(tk._tkinter.DONT_WAIT | tk._tkinter.WINDOW_EVENTS | tk._tkinter.IDLE_EVENTS)
        self.after(100, self.check_signals) # ตรวจสอบทุกๆ 100 มิลลิวินาที

    def quit_app(self):
        set_relay_state(RELAY_OFF_STATE) # ตรวจสอบให้แน่ใจว่า Relay ปิดก่อน cleanup
        GPIO.cleanup()
        print("GPIO cleanup เสร็จสิ้น")
        """ฟังก์ชันสำหรับปิดแอปพลิเคชันอย่างสมบูรณ์"""
        self._cancel_all_timers() # ยกเลิก Timer ทั้งหมด
        self.destroy() # ทำลายหน้าต่าง Tkinter
        sys.exit(0) # ออกจากโปรแกรม Python อย่างสมบูรณ์
    # --- จบการเพิ่มฟังก์ชันสำหรับจัดการ SIGINT (Ctrl+C) ---

# --- ส่วนของการรันแอปพลิเคชัน ---
if __name__ == "__main__":
    try:
        from PIL import Image, ImageTk
    except ImportError:
        messagebox.showerror("ข้อผิดพลาด", "ไม่พบไลบรารี Pillow\nกรุณาติดตั้งด้วยคำสั่ง: pip install Pillow")
        sys.exit(1)

    app = MoneyExchangeApp()
    app.mainloop()
