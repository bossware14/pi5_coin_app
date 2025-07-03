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

try:
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
    time.sleep(2) # รอสักครู่ก่อนเริ่ม
    start_dispensing(2) # สั่งจ่าย 2 เหรียญ

    # ทำให้โปรแกรมทำงานไปเรื่อยๆ เพื่อรอ event และการควบคุม
    while True:
        time.sleep(0.1) # หน่วงเวลาเล็กน้อยเพื่อไม่ให้ CPU ทำงานหนักเกินไป

except KeyboardInterrupt:
    print("\nหยุดการทำงาน...")
finally:
    # ทำความสะอาด GPIO เมื่อโปรแกรมหยุด
    set_relay_state(RELAY_OFF_STATE) # ตรวจสอบให้แน่ใจว่า Relay ปิดก่อน cleanup
    GPIO.cleanup()
    print("GPIO cleanup เสร็จสิ้น")

