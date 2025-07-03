# Raspberry Pi5(1) Relay (1) เครื่องนับธนบัตร (1) และ เครื่องจ่ายเหรียญ (1)
import RPi.GPIO as GPIO
import time
import threading
import queue

# กำหนดโหมดของ GPIO
GPIO.setmode(GPIO.BCM)

# กำหนดขา GPIO
BILER_SENSOR_PIN = 6  # ขาสำหรับตรวจจับเซนเซอร์ ธนบัตร (นับการกะพริบ)
COIN_SENSOR_PIN = 12  # ขาสำหรับตรวจจับการหมุนของเซ็นเซอร์เหรียญ
GPIO_RELAY = 26       # ขาสำหรับควบคุม Relay (เช่น เครื่องจ่ายเหรียญ)

# ตัวแปรสถานะ
coins_to_dispense_target = 0 # จำนวนเหรียญที่ต้องการให้จ่าย (เป้าหมาย)
coins_dispensed_count = 0    # จำนวนเหรียญที่ถูกจ่ายออกไปแล้วจริง
is_dispensing_active = False # สถานะว่ากำลังอยู่ในกระบวนการจ่ายเหรียญหรือไม่

# --- ตัวแปรสำหรับจัดการ Biller Pulse Counting ---
bill_pulse_count = 0 # จำนวนพัลส์ที่นับได้สำหรับธนบัตรใบปัจจุบัน
last_bill_pulse_time = 0 # เวลาล่าสุดที่ตรวจจับพัลส์ของธนบัตร
BILL_PULSE_TIMEOUT = 1.0 # วินาที: ระยะเวลาสูงสุดที่ไม่มีการกะพริบก่อนที่จะถือว่าการนับจบ
# Mapping จำนวนพัลส์กับมูลค่าธนบัตร
BILL_PULSE_MAPPING = {
    2: 20,   # 2 พัลส์ = 20 บาท
    5: 50,   # 5 พัลส์ = 50 บาท
    10: 100, # 10 พัลส์ = 100 บาท
    50: 500, # 50 พัลส์ = 500 บาท
    100: 1000 # 100 พัลส์ = 1000 บาท (ถ้ามี)
}
# --- จบส่วนตัวแปร Biller ---

# Queue สำหรับส่งมูลค่าธนบัตรที่ยืนยันแล้วไปยังเธรดประมวลผล
biller_value_queue = queue.Queue()

# กำหนด Relay เป็น Active Low หรือ Active High
RELAY_ON_STATE = GPIO.LOW  # สมมติว่า Relay ของคุณเป็น Active Low
RELAY_OFF_STATE = GPIO.HIGH

# ฟังก์ชันสำหรับควบคุม Relay
def set_relay_state(state):
    """
    ตั้งค่าสถานะของ Relay (เปิด/ปิด)
    """
    GPIO.output(GPIO_RELAY, state)
    print(f"Relay state set to: {'ON' if state == RELAY_ON_STATE else 'OFF'}")

# ฟังก์ชัน Callback เมื่อมีการกะพริบของเซ็นเซอร์ธนบัตร (Biller Pulse)
def biler_sensor_callback(channel):
    """
    Callback สำหรับเซ็นเซอร์ธนบัตร
    นับจำนวนพัลส์และอัปเดตเวลาล่าสุดที่ตรวจจับพัลส์
    """
    global bill_pulse_count, last_bill_pulse_time
    current_state = GPIO.input(channel)
    
    # ตรวจจับขอบขาขึ้น (RISING) หรือขอบขาลง (FALLING) ที่เป็น Pulse
    # ตามที่คุณบอกว่า "กะพริบ" ซึ่งมักหมายถึงการเปลี่ยนสถานะไปกลับ
    # สำหรับเซ็นเซอร์ที่กะพริบหลายครั้งเพื่อส่งค่า ควรใช้ GPIO.BOTH
    # และนับทุกการเปลี่ยนสถานะ หรือเลือกเฉพาะ RISING/FALLING ที่เป็น Pulse ที่แท้จริง
    # สำหรับตัวอย่างนี้ ผมจะสมมติว่าคุณนับทุกครั้งที่เกิด RISING edge ของ pulse
    
    if current_state == GPIO.HIGH: # ถ้าตรวจจับ RISING edge
        bill_pulse_count += 1
        last_bill_pulse_time = time.time()
        print(f"Biller Pulse Detected! Count: {bill_pulse_count}")

# ฟังก์ชัน Callback เมื่อเซ็นเซอร์เหรียญตรวจจับการหมุน
def coin_sensor_callback(channel):
    """
    Callback สำหรับเซ็นเซอร์เหรียญ
    นับจำนวนเหรียญที่ถูกจ่ายออกไป และหยุด Relay เมื่อจ่ายครบตามเป้าหมาย
    """
    global coins_dispensed_count, is_dispensing_active
    current_state = GPIO.input(channel)
    
    # ตรวจจับขอบขาขึ้น (RISING) หรือปรับเป็น FALLING/BOTH ตามเซ็นเซอร์ของคุณ
    if current_state == GPIO.HIGH and is_dispensing_active:
        coins_dispensed_count += 1
        print(f"ตรวจจับเหรียญที่จ่ายออก: {coins_dispensed_count} / {coins_to_dispense_target}")
        
        if coins_dispensed_count >= coins_to_dispense_target:
            print("จ่ายเหรียญครบแล้ว หยุดการทำงานของ Relay")
            is_dispensing_active = False
            set_relay_state(RELAY_OFF_STATE) # ปิด Relay

# ฟังก์ชันสำหรับเริ่มกระบวนการจ่ายเหรียญ
def start_dispensing(num_coins):
    """
    เริ่มต้นกระบวนการจ่ายเหรียญตามจำนวนที่กำหนด
    """
    global coins_to_dispense_target, coins_dispensed_count, is_dispensing_active

    if is_dispensing_active:
        print("กำลังจ่ายเหรียญอยู่ โปรดรอให้เสร็จสิ้น")
        return

    if num_coins <= 0:
        print("จำนวนเหรียญที่ต้องการจ่ายต้องมากกว่า 0")
        return

    print(f"เริ่มจ่ายเหรียญจำนวน {num_coins} เหรียญ...")
    coins_to_dispense_target = num_coins
    coins_dispensed_count = 0
    is_dispensing_active = True
    set_relay_state(RELAY_ON_STATE) # เปิด Relay เพื่อเริ่มจ่ายเหรียญ

# ฟังก์ชันสำหรับประมวลผลมูลค่าธนบัตรและสั่งจ่ายเหรียญ (ทำงานใน Thread แยก)
def process_bill_and_dispense():
    """
    เธรดสำหรับตรวจสอบจำนวนพัลส์ธนบัตรที่นับได้จาก Biller Callback
    และสั่งจ่ายเหรียญตามมูลค่าที่ยืนยันแล้ว
    """
    global bill_pulse_count, last_bill_pulse_time, is_dispensing_active

    while True:
        current_time = time.time()
        
        # ตรวจสอบว่ามีพัลส์ถูกนับเข้ามา และผ่านช่วง Timeout ไปแล้ว
        # นั่นหมายความว่าการนับสำหรับธนบัตรใบนี้ได้สิ้นสุดลง
        if bill_pulse_count > 0 and (current_time - last_bill_pulse_time) > BILL_PULSE_TIMEOUT:
            print(f"Biller pulse counting finished. Total pulses: {bill_pulse_count}")
            
            # ตรวจสอบมูลค่าธนบัตรจากจำนวนพัลส์ที่นับได้
            detected_bill_value = BILL_PULSE_MAPPING.get(bill_pulse_count)
            
            if detected_bill_value:
                if not is_dispensing_active:
                    print(f"ตรวจพบธนบัตร {detected_bill_value} บาท (จาก {bill_pulse_count} พัลส์)")
                    # แปลงมูลค่าธนบัตรเป็นจำนวนเหรียญที่ต้องการจ่าย (สมมติ 1 เหรียญ = 10 บาท)
                    num_coins_to_dispense = detected_bill_value // 10 
                    start_dispensing(num_coins_to_dispense)
                else:
                    print(f"ได้รับธนบัตร {detected_bill_value} บาท แต่กำลังจ่ายเหรียญอยู่ โปรดรอ.")
            else:
                print(f"ตรวจพบจำนวนพัลส์ที่ไม่ตรงกับมูลค่าที่รู้จัก: {bill_pulse_count} ครั้ง (อาจมีปัญหา)")
            
            # รีเซ็ตตัวนับพัลส์หลังจากประมวลผลแล้ว
            bill_pulse_count = 0
            last_bill_pulse_time = 0

        # อาจจะมีการประมวลผล Queue ในอนาคตถ้ามีแหล่งข้อมูลอื่นส่งเข้ามา
        try:
            # ลองดึงข้อมูลจาก biller_value_queue (เผื่อใช้ในอนาคต หากมีแหล่งอื่นส่งมูลค่าเข้ามา)
            # ตัวอย่างนี้จะไม่ได้ใช้ queue โดยตรง ถ้า logic ทั้งหมดอยู่ใน process_bill_and_dispense
            # แต่ถ้ามีการเชื่อมต่อ API หรือปุ่มที่สามารถสั่งจ่ายได้โดยตรง ก็ยังใช้ queue นี้ได้
            bill_value_from_queue = biller_value_queue.get(timeout=0.01) # Non-blocking read
            print(f"Received value from external queue: {bill_value_from_queue}")
            # สามารถเพิ่ม logic การจ่ายเหรียญจาก queue ตรงนี้ได้
            biller_value_queue.task_done()
        except queue.Empty:
            pass # ไม่มีข้อมูลใน queue
        except Exception as e:
            print(f"Error reading from queue in process_bill_and_dispense: {e}")

        time.sleep(0.01) # หน่วงเวลาเล็กน้อยเพื่อให้เธรดอื่นๆ ทำงาน

try:
    # ตั้งค่าขา Relay เป็น Output และเริ่มต้นด้วยการปิด Relay ไว้
    GPIO.setup(GPIO_RELAY, GPIO.OUT, initial=RELAY_OFF_STATE)
    print("ตั้งค่า Relay พร้อมใช้งาน")
    
    # ตั้งค่าขา Input พร้อม Pull-up สำหรับเซ็นเซอร์
    GPIO.setup(COIN_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BILER_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # เพิ่ม event detection สำหรับขา BILER_SENSOR_PIN
    # ใช้ GPIO.RISING หรือ GPIO.FALLING หรือ GPIO.BOTH ขึ้นอยู่กับลักษณะ Pulse ของเซ็นเซอร์ธนบัตร
    # bouncetime ควรจะสั้นพอที่จะจับทุก Pulse แต่ก็ยาวพอที่จะป้องกันการสั่นของหน้าสัมผัส
    # สำหรับการนับ Pulse ผมแนะนำให้ใช้ bouncetime ที่น้อยมาก เช่น 1-5 ms หรือจัดการ Debounce ด้วย Software เอง
    # แต่ถ้า Biller Sensor ให้แค่ 2, 5, 10 Pulse ที่ชัดเจน และมี Delay ระหว่าง Pulse ที่มากพอ
    # bouncetime 20ms อาจจะพอได้ ถ้า Pulse ไม่ได้ถี่มาก
    GPIO.add_event_detect(BILER_SENSOR_PIN, GPIO.RISING, callback=biler_sensor_callback, bouncetime=20) 
    
    # เพิ่ม event detection สำหรับขา COIN_SENSOR_PIN
    # เลือก GPIO.RISING, GPIO.FALLING หรือ GPIO.BOTH ให้เหมาะสมกับเซ็นเซอร์เหรียญของคุณ
    GPIO.add_event_detect(COIN_SENSOR_PIN, GPIO.RISING, callback=coin_sensor_callback, bouncetime=50) 

    print("เริ่มต้นเธรดสำหรับประมวลผลธนบัตรและจ่ายเหรียญ...")
    # เรียกฟังก์ชัน process_bill_and_dispense ใน Thread แยก
    process_thread = threading.Thread(target=process_bill_and_dispense)
    process_thread.daemon = True # ทำให้เธรดนี้ปิดเองเมื่อโปรแกรมหลักปิด
    process_thread.start()

    print(f"ระบบพร้อมทำงาน: รอการเปลี่ยนแปลงสถานะบน GPIO {COIN_SENSOR_PIN} (เซ็นเซอร์เหรียญ) และ {BILER_SENSOR_PIN} (เซ็นเซอร์ธนบัตร)...")
    print("กด Ctrl+C เพื่อหยุดการทำงาน")
    
    # ทำให้โปรแกรมหลักทำงานไปเรื่อยๆ เพื่อรอ Event จาก GPIO และการทำงานของเธรด
    while True:
        time.sleep(1) # หน่วงเวลาเล็กน้อย เพื่อให้เธรดอื่นทำงานและลด CPU usage

except KeyboardInterrupt:
    print("\nหยุดการทำงานโดยผู้ใช้...")
finally:
    # ทำความสะอาด GPIO เมื่อโปรแกรมหยุดทำงาน
    set_relay_state(RELAY_OFF_STATE) # ตรวจสอบให้แน่ใจว่า Relay ปิดก่อน cleanup
    GPIO.cleanup()
    print("GPIO cleanup เสร็จสิ้น")

