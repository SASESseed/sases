import zipfile
import os

def zip_data():
    file = "finetune_data.jsonl"
    if not os.path.exists(file):
        print(f"{file} 不存在，请先运行 export_finetune_data.py")
        return
    with zipfile.ZipFile("finetune_data.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(file)
    print("已打包: finetune_data.zip")

if __name__ == "__main__":
    zip_data()
