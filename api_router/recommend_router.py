"""
推荐接口
GET /api/recommend/personalized   个性化推荐
GET /api/recommend/hot            热门推荐
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from auth_load.jwt_util import get_current_user
from auth_load.permission import filter_accessible_documents
from database.models import get_db, User, ChatHistory, Document
from models.Pydantic_schemas import NeedResponseModel

recommend_router = APIRouter(prefix='/recommend')


@recommend_router.get('/personalized')
async def personalized_recommend(
        top_k: int = Query(5, ge=1, le=20),
        db: Session = Depends(get_db),
        current_user: tuple[User, str] = Depends(get_current_user)
):
    """个性化推荐 - 基于用户历史查询和部门偏好"""
    # 1. 获取用户历史查询过的关键词
    user, token = current_user
    history = db.query(ChatHistory.content) \
        .filter(ChatHistory.user_id == user.id, ChatHistory.role == "user") \
        .order_by(ChatHistory.created_at.desc()) \
        .limit(20) \
        .all()
    recent_queries = [h.content for h in history]

    # 2. 获取全部在库文档，并按角色/密级/部门权限过滤出用户可访问的
    docs = db.query(Document) \
        .filter(Document.status == "active") \
        .all()
    accessible_docs = filter_accessible_documents(user, docs)

    # 3. 基于标签匹配推荐
    user_tags = set()
    for q in recent_queries:
        for word in q.replace('，', ' ').replace('。', ' ').replace('？', ' ').split():
            if len(word) >= 2:
                user_tags.add(word)

    scored_docs = []
    for doc in accessible_docs:
        score = 0
        doc_tags = doc.tags if doc.tags else []
        # 标签匹配加分
        for tag in doc_tags:
            tag_name = tag.get("name", "") if isinstance(tag, dict) else str(tag)
            for qt in recent_queries:
                if tag_name in qt:
                    score += 2
        # 公开文档额外加分
        if doc.permission == "public":
            score += 1
        scored_docs.append((doc, score))

    # 4. 按分数排序取 top_k
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    results = []
    for doc, score in scored_docs[:top_k]:
        results.append({
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "department": doc.department,
            "permission": doc.permission,
            "tags": doc.tags,
        })

    return NeedResponseModel(code=200, message="推荐成功", data=results)


@recommend_router.get('/hot')
async def hot_recommend(
        top_k: int = Query(10, ge=1, le=50),
        db: Session = Depends(get_db),
        current_user: tuple[User, str] = Depends(get_current_user)
):
    """热门推荐 - 最近上传的文档（按用户角色/密级/部门权限过滤）"""
    user, token = current_user
    results = []

    # 如果反馈数据不足，补充最近上传的文档（按用户权限过滤）
    if len(results) < top_k:
        recent_docs = db.query(Document) \
            .filter(Document.status == "active") \
            .order_by(Document.created_at.desc()) \
            .all()
        accessible_docs = filter_accessible_documents(user, recent_docs)
        for doc in accessible_docs[:top_k]:
            if not any(r["doc_id"] == doc.doc_id for r in results):
                results.append({
                    "doc_id": doc.doc_id,
                    "filename": doc.filename,
                    "department": doc.department,
                    "permission": doc.permission,
                    "tags": doc.tags,
                    "hot_score": 0,
                })

    return NeedResponseModel(code=200, message="查询成功", data=results)
