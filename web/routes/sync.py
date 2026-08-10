# web/routes/sync.py
"""
数据同步 API 路由.

供新节点加入时拉取全量历史数据.
"""

from fastapi import APIRouter, HTTPException
from storage import repositories as repo

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/")
async def get_all_data():
    """
    获取全量数据（帖子 + 评论 + 审核日志）.

    新节点加入时调用此接口拉取所有历史数据.
    """
    try:
        data = repo.get_all_data_for_sync()
        return {
            "status": "success",
            "data": {
                "posts": data["posts"],
                "comments": data["comments"],
                "audit_logs": data["audit_logs"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步数据失败: {str(e)}")