from core.mongo import users_col
from bson import ObjectId

# 查找这个用户
user_id = "69b42d2f98beef4130edaffc"
user = users_col.find_one({"_id": ObjectId(user_id)})
print("找到的用户:", user)

# 或者查找所有用户
all_users = list(users_col.find())
print("所有用户:")
for u in all_users:
    print(f"  - {u['_id']}: {u['username']} (status: {u.get('status', 'unknown')})")
