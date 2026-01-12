import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io

# إعداد الاتصال
FOLDER_ID = "1kgzKj9sn8pQVjr78XcN7_iF5KLmflwME"
creds = service_account.Credentials.from_service_account_file('credentials.json')
service = build('drive', 'v3', credentials=creds)

print("🕵️‍♂️ جاري قراءة أسماء الأعمدة من الملفات...\n")

results = service.files().list(
    q=f"'{FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)").execute()

files = results.get('files', [])

for file in files:
    print(f"📂 الملف: {file['name']}")
    try:
        # تحميل جزء صغير من الملف لقراءة العناوين فقط
        request = service.files().get_media(fileId=file['id'])
        downloaded = io.BytesIO(request.execute())
        
        # محاولة قراءة الملف
        try:
            df = pd.read_csv(downloaded, nrows=2) # نقرأ سطرين فقط
        except:
            # محاولة أخرى بترميز مختلف لو كان عربي
            downloaded.seek(0)
            df = pd.read_csv(downloaded, nrows=2, encoding='utf-8-sig')

        print("   📌 الأعمدة الموجودة:")
        print(f"   {list(df.columns)}")
        print("-" * 50)
        
    except Exception as e:
        print(f"   ❌ لم نستطع قراءة الملف: {e}")
        print("-" * 50)
