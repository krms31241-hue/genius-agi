from executive.resource_manager import ResourceManager
manager = ResourceManager()
print("\n=== تم تحديث الملف بنجاح! الاستهلاك الحالي للموارد ===")
print(manager.get_usage())
