from google.oauth2 import service_account
from googleapiclient.discovery import build

# كود المجلد الخاص بك
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"

print("🕵️‍♂️ جاري فحص محتويات المجلد...")

try:
    # الاتصال
    creds = service_account.Credentials.from_service_account_file('credentials.json')
    service = build('drive', 'v3', credentials=creds)

    # جلب قائمة الملفات (بدون فلترة النوع)
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name, mimeType)").execute()
    
    files = results.get('files', [])

    if not files:
        print("\n⚠️ المجلد فارغ تماماً!")
        print("تأكد أنك رفعت الملف داخل المجلد الصحيح في Google Drive.")
    else:
        print(f"\n✅ وجدنا {len(files)} ملفات داخل المجلد:")
        print("-" * 40)
        for file in files:
            print(f"📄 الاسم: {file['name']}")
            print(f"   النوع: {file['mimeType']}")
            
            if 'csv' not in file['mimeType'] and 'spreadsheet' not in file['mimeType']:
                 print("   ❌ (تنبيه: هذا الملف ليس CSV ولن يقرأه الروبوت)")
            else:
                 print("   ✅ (نوع الملف صحيح)")
            print("-" * 40)

except Exception as e:
    print(f"\n❌ خطأ في الاتصال: {e}")
