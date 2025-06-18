# from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Request, Depends, HTTPException
from app.data.models import User

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# # JWT工具方法
# def create_access_token(data: dict):
#     expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode = data.copy()
#     expire = datetime.utcnow() + expires_delta
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# # 权限验证依赖项
# async def get_current_admin(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=401,
#         detail="无法验证凭证",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         if payload.get("role") != "admin":
#             raise credentials_exception
#         return payload
#     except JWTError:
#         raise credentials_exception

# # 二次确认机制
# async def require_confirmation(
#     confirmation: bool = Query(False, description="请确认删除操作")
# ):
#     if not confirmation:
#         raise HTTPException(
#             status_code=400,
#             detail="需要二次确认参数confirm=true"
#         )



async def get_current_user(request: Request):
    if "current_user" not in request.session:
        raise HTTPException(status_code=403, detail="请先登录")
    return request.session["current_user"]

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user

async def require_operator(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Operator":
        raise HTTPException(status_code=403, detail="需要操作员权限")
    return current_user