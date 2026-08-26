import json, os, re, uuid, time
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from rank_bm25 import BM25Okapi

import auth

app = FastAPI(title="SASES Seed Submission API", version="0.1.0")

KB_FILE = "success_kb.json"
SEED_POOL_FILE = "seed_tasks_external.jsonl"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class SeedSubmitRequest(BaseModel):
    description: str
    test_cases: list = []

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = auth.get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    return user

@app.post("/submit_seed")
async def submit_seed(req: SeedSubmitRequest, current_user=Depends(get_current_user)):
    if not req.description or len(req.description) < 10:
        raise HTTPException(status_code=400, detail="任务描述过短")
    
    # 生成标准种子格式
    seed = {
        "id": str(uuid.uuid4()),
        "description": req.description,
        "test_cases": req.test_cases if req.test_cases else [],
        "source": "external_api",
        "user_id": current_user["id"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 追加到外部种子池
    with open(SEED_POOL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(seed, ensure_ascii=False) + "\n")
    
    return {"message": "种子已提交，等待处理", "seed": seed}

@app.get("/external_seed_count")
async def external_seed_count(current_user=Depends(get_current_user)):
    if not os.path.exists(SEED_POOL_FILE):
        return {"count": 0}
    with open(SEED_POOL_FILE, "r", encoding="utf-8") as f:
        count = sum(1 for _ in f)
    return {"count": count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
