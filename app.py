import asyncio
import os
import time
import multiprocessing
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pyppeteer import launch

# دالة التحميل التي تعمل في عملية منفصلة (Process)
def run_process_worker(hhh, save_path, page_format, result_file):
    # إنشاء حدث غير متزامن داخل العملية المستقلة
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(async_main_download(hhh, save_path, page_format, result_file))
    finally:
        loop.close()

async def async_main_download(hhh, save_path, page_format, result_file):
    for h in range(len(hhh)):
        url = hhh[h]
        try:
            await accept_cookies(url, h + 1, save_path, page_format, result_file)
        except Exception as e:
            current_time = time.strftime("%H-%M-%S")
            with open(result_file, "a", encoding="utf-8") as file2:
                file2.write(f"{url}\tError: {str(e)}\t{current_time}\n")

async def accept_cookies(url, index, save_path, page_format, result_file):
    # تحديد مسار Google Chrome المثبت على الجهاز تلقائياً
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    launch_args = {'headless': True}
    if os.path.exists(chrome_path):
        launch_args['executablePath'] = chrome_path

    browser = await launch(**launch_args)
    page = await browser.newPage()
    
    await page.goto(url, {'timeout': 30000, 'waitUntil': 'networkidle2'})
    await page.waitForSelector('#swal2-html-container > div > div > div.cc-body > div.row > div > div > button.custom-button.--primary')
    
    accept_button = await page.querySelector('#swal2-html-container > div > div > div.cc-body > div.row > div > div > button.custom-button.--primary')
    await asyncio.sleep(0.1)
    await accept_button.click()
    await asyncio.sleep(0.1)
    
    await page.emulateMedia('screen')
    current_time = time.strftime("%H-%M-%S")
    file_name = f"File_{current_time}_{index}.pdf"
    
    await page.pdf({
        'path': f"{save_path}{file_name}",
        'printBackground': True,
        'format': page_format
    })
    
    with open(result_file, "a", encoding="utf-8") as file2:
        file2.write(f"{url}\t{file_name}\t{current_time}\n")

    await browser.close()


class RittalDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rittal PDF Downloader")
        self.root.geometry("500x450")
        self.root.resizable(False, False)

        # المتغيرات
        self.path_var = tk.StringVar(value=os.getcwd())
        self.format_var = tk.StringVar(value="A4")
        self.worker_process = None

        self.create_widgets()

    def create_widgets(self):
        title_label = tk.Label(self.root, text="Rittal PDF Downloader - GUI", font=("Arial", 14, "bold"))
        title_label.pack(pady=15)

        # اختيار المجلد
        frame_path = tk.Frame(self.root)
        frame_path.pack(fill="x", padx=20, pady=5)
        
        tk.Label(frame_path, text="مجلد الحفظ:", font=("Arial", 10)).pack(side="right", padx=5)
        self.entry_path = tk.Entry(frame_path, textvariable=self.path_var, font=("Arial", 10), width=30)
        self.entry_path.pack(side="right", padx=5)
        tk.Button(frame_path, text="استعراض", command=self.browse_path).pack(side="right")

        # اختيار حجم الصفحة
        frame_format = tk.Frame(self.root)
        frame_format.pack(fill="x", padx=20, pady=10)
        
        tk.Label(frame_format, text="حجم الصفحة:", font=("Arial", 10)).pack(side="right", padx=5)
        formats = ["A0", "A1", "A2", "A3", "A4"]
        format_menu = ttk.Combobox(frame_format, textvariable=self.format_var, values=formats, state="readonly", width=15)
        format_menu.pack(side="right", padx=5)

        # زر البدء
        self.btn_start = tk.Button(self.root, text="بدء التحميل", bg="green", fg="white", font=("Arial", 12, "bold"), command=self.start_process, width=20, height=2)
        self.btn_start.pack(pady=20)

        # شريط التقدم وحالة العمل
        self.progress_label = tk.Label(self.root, text="الوضع: جاهز للبدء", font=("Arial", 10))
        self.progress_label.pack(pady=5)
        
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)

    def browse_path(self):
        dir_selected = filedialog.askdirectory()
        if dir_selected:
            self.path_var.set(dir_selected)

    def start_process(self):
        p = self.path_var.get()
        if p and p[-1] != "\\":
            p = p + "\\"
            
        page_format = self.format_var.get()
        result_file = "Rittal Download Result.txt"

        # قراءة الروابط
        try:
            with open('Links.txt', 'r', encoding="utf-8") as f:
                hhh = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            messagebox.showerror("خطأ", "ملف Links.txt غير موجود في نفس المجلد!")
            return

        if not hhh:
            messagebox.showwarning("تحذير", "ملف Links.txt فارغ!")
            return

        self.btn_start.config(state="disabled")
        self.progress["maximum"] = len(hhh)
        self.progress["value"] = len(hhh) # مؤشر اكتمال شكلي أو يمكن جعله غير محدد

        # إنشاء ملف النتائج
        with open(result_file, "w", encoding="utf-8") as f:
            f.write("Link\tFile Name\tTime\n")

        self.progress_label.config(text="جاري التحميل في عملية منفصلة...")

        # تشغيل التحميل عبر Process مستقلة تماماً لتجنب مشاكل الـ Signal والثريدز
        self.worker_process = multiprocessing.Process(
            target=run_process_worker,
            args=(hhh, p, page_format, result_file)
        )
        self.worker_process.start()

        # مراقبة انتهاء العملية في الخلفية دون تجميد الواجهة
        self.root.after(100, self.check_process)

    def check_process(self):
        if self.worker_process and self.worker_process.is_alive():
            # العملية لا تزال تعمل، تحقق مرة أخرى بعد نصف ثانية
            self.root.after(500, self.check_process)
        else:
            # انتهت العملية بنجاح
            self.progress_label.config(text="اكتمل التحميل بنجاح!")
            self.btn_start.config(state="normal")
            messagebox.showinfo("تم", "تم الانتهاء من تحميل جميع الروابط بنجاح!")


if __name__ == "__main__":
    # ضروري جداً لضمان عمل الـ Multiprocessing بشكل صحيح مع ملفات الـ .exe
    multiprocessing.freeze_support()
    
    root = tk.Tk()
    app = RittalDownloaderApp(root)
    root.mainloop()
