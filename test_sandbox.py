from lab.sandbox import run

print("\n=== جاري اختبار الصندوق الآمن (Sandbox) ===")
# هنجرب نشغل أمر طباعة بسيط من خلال الكود بتاعك
result = run(["echo", "تم تشغيل Sandbox بنجاح على الترمينال!"])

print(f"الأمر اللي اتنفذ: {result.command}")
print(f"النتيجة: {result.stdout.strip()}")
print(f"رمز الخروج: {result.exit_code}")
print(f"الوقت المستغرق: {result.duration:.4f} ثانية")
print("==========================================\n")
