import schedule
import time
import threading
from src.routes.notifications import NotificationService

class NotificationScheduler:
    """جدولة التنبيهات التلقائية"""
    
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
    
    def start(self):
        """بدء جدولة التنبيهات"""
        if not self.running:
            self.running = True
            
            # جدولة معالجة التنبيهات كل ساعة
            schedule.every().hour.do(self._process_notifications)
            
            # جدولة معالجة التنبيهات اليومية في الساعة 9 صباحاً
            schedule.every().day.at("09:00").do(self._process_daily_notifications)
            
            # بدء الخيط
            self.thread = threading.Thread(target=self._run_scheduler)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """إيقاف جدولة التنبيهات"""
        self.running = False
        schedule.clear()
    
    def _run_scheduler(self):
        """تشغيل الجدولة"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # فحص كل دقيقة
    
    def _process_notifications(self):
        """معالجة التنبيهات"""
        with self.app.app_context():
            try:
                NotificationService.process_notification_rules()
                print(f"تم معالجة قواعد التنبيهات في {time.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                print(f"خطأ في معالجة التنبيهات: {e}")
    
    def _process_daily_notifications(self):
        """معالجة التنبيهات اليومية"""
        with self.app.app_context():
            try:
                # معالجة التنبيهات اليومية الخاصة
                NotificationService.process_notification_rules()
                print(f"تم معالجة التنبيهات اليومية في {time.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                print(f"خطأ في معالجة التنبيهات اليومية: {e}")

