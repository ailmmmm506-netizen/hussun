from google.oauth2 import service_account
from googleapiclient.discovery import build
import io

# إعداد الاتصال
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
creds = service_account.Credentials.from_service_account_file('credentials.json')
service = build('drive', 'v3', credentials=creds)

print("🕵️‍♂️ جاري فحص ملفات MOJ...\n")

results = service.files().list(
    q=f"'{FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)").execute()

files = results.get('files', [])

for file in files:
    if 'MOJ' in file['name'].upper():
        print(f"📂 وجدنا الملف: {file['name']}")
        print("   جاري قراءة أول 5 أسطر كما هي (Raw Text)...")
        print("-" * 50)
        
        try:
            request = service.files().get_media(fileId=file['id'])
            # نقرأ أول 1000 حرف فقط
            content = request.execute()[:1000] 
            
            # نحاول طباعتها لنرى شكل الفواصل
            try:
                print(content.decode('utf-8'))
            except:
                print("⚠️ فشل ترميز utf-8، نجرب utf-16...")
                print(content.decode('utf-16'))
                
        except Exception as e:
            print(f"❌ خطأ في القراءة: {e}")
            
        print("-" * 50)