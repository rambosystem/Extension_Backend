from app.db.database import engine, Base, SessionLocal
from app.models.user import User

# 创建表
Base.metadata.create_all(bind=engine)

# 插入测试数据
db = SessionLocal()
try:
    test_user = User(name="Alice", email="alice@example.com")
    db.add(test_user)
    db.commit()
    print("✅ Test user inserted.")
except Exception as e:
    print(f"❌ Failed to insert: {e}")
    db.rollback()
finally:
    db.close()
