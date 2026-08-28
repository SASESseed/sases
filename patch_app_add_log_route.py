with open("app_full.py", "r", encoding="utf-8") as f:
    content = f.read()

new_route = '''
@app.get("/admin/contribution_logs")
async def admin_contribution_logs(limit: int = 50, current_user=Depends(get_current_user)):
    if not auth.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="仅管理员可用")
    logs = contribution_log.get_all_logs(limit)
    return {"logs": logs}
'''

anchor = "# ---------- 防篡改校验 ----------"
if anchor in content:
    content = content.replace(anchor, new_route + "\n" + anchor)
    print("已插入管理员日志接口。")
else:
    print("警告：未找到锚点，请检查 app_full.py")

with open("app_full.py", "w", encoding="utf-8") as f:
    f.write(content)

print("补丁完成！")
