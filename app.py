import os
import shutil
import subprocess
import uuid
import zipfile
from flask import Flask, request, send_file, render_template_string

app = Flask(__name__)

UPLOAD_DIR = "/tmp/generated_apks"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ডিবাগ কীস্টোর তৈরি (যদি না থাকে)
KEYSTORE_PATH = "/tmp/debug.keystore"
if not os.path.exists(KEYSTORE_PATH):
    subprocess.run([
        "keytool", "-genkey", "-v",
        "-keystore", KEYSTORE_PATH,
        "-alias", "androiddebugkey",
        "-storepass", "android",
        "-keypass", "android",
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-dname", "CN=Android Debug,O=Android,C=US"
    ], check=True)

# HTML ওয়েব পেজের ডিজাইন (UI)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>APK Builder Pro</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #fff; padding: 20px; display: flex; justify-content: center; }
        .box { background: #1e293b; padding: 30px; border-radius: 12px; width: 100%; max-width: 500px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        h2 { text-align: center; color: #38bdf8; }
        input, textarea, button { width: 100%; margin-top: 10px; border-radius: 6px; border: 1px solid #334155; box-sizing: border-box; }
        input, textarea { background: #0f172a; color: #fff; padding: 10px; }
        textarea { height: 160px; font-family: monospace; }
        button { background: #0284c7; color: white; padding: 12px; font-size: 16px; font-weight: bold; cursor: pointer; border: none; }
        button:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div class="box">
        <h2>🛠️ HTML to APK Builder</h2>
        <form action="/build" method="POST">
            <label>অ্যাপের নাম (App Name):</label>
            <input type="text" name="app_name" value="MyGameApp" required>
            
            <label style="margin-top: 15px; display:block;">HTML কোড দিন:</label>
            <textarea name="html_code" required><h1>স্বাগতম! আমার নতুন অ্যাপ</h1><p>এটি কাজ করছে!</p></textarea>
            
            <button type="submit">APK তৈরি এবং ডাউনলোড করুন</button>
        </form>
    </div>
</body>
</html>
"""

def build_and_sign_apk(html_code, app_name):
    unique_id = str(uuid.uuid4())[:8]
    work_dir = f"/tmp/build_{unique_id}"
    os.makedirs(work_dir, exist_ok=True)

    base_apk = "base_template.apk"
    if not os.path.exists(base_apk):
        raise FileNotFoundError("base_template.apk ফাইলটি সার্ভারে পাওয়া যায়নি!")

    temp_apk = os.path.join(work_dir, "temp.apk")
    aligned_apk = os.path.join(work_dir, "aligned.apk")
    final_apk = os.path.join(UPLOAD_DIR, f"{app_name}_{unique_id}.apk")

    shutil.copy(base_apk, temp_apk)

    # HTML ফাইল তৈরি
    assets_dir = os.path.join(work_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    with open(os.path.join(assets_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_code)

    # APK-এর ভেতর index.html ইনজেক্ট করা
    with zipfile.ZipFile(temp_apk, 'a') as zip_ref:
        zip_ref.write(os.path.join(assets_dir, "index.html"), "assets/index.html")

    # Zipalign করা
    subprocess.run(["zipalign", "-f", "-p", "4", temp_apk, aligned_apk], check=True)

    # V2/V3 Signature যুক্ত করা (যাতে Parse Error না আসে)
    subprocess.run([
        "apksigner", "sign",
        "--ks", KEYSTORE_PATH,
        "--ks-pass", "pass:android",
        "--key-pass", "pass:android",
        "--ks-key-alias", "androiddebugkey",
        "--out", final_apk,
        aligned_apk
    ], check=True)

    shutil.rmtree(work_dir)
    return final_apk

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/build', methods=['POST'])
def build_apk():
    html_code = request.form.get('html_code', '')
    app_name = request.form.get('app_name', 'MyApp').replace(" ", "_")

    try:
        apk_path = build_and_sign_apk(html_code, app_name)
        return send_file(apk_path, as_attachment=True, download_name=f"{app_name}.apk")
    except Exception as e:
        return f"<h3>বিল্ড এরর: {str(e)}</h3>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
