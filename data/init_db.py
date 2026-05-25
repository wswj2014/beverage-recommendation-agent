"""Beverage database initialization — create tables and seed 22 Luckin-style drinks."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS beverages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    temperature TEXT NOT NULL,
    sweetness TEXT NOT NULL,
    price REAL NOT NULL,
    popularity INTEGER DEFAULT 50,
    tags TEXT DEFAULT '[]',
    description TEXT
);
"""

SEED_DATA = [
    ("冰美式", "咖啡", "冰", "无糖", 15.0, 92, '["提神","经典","低卡","清爽"]', "经典冰美式，醇苦提神，夏日必备清醒神器"),
    ("热美式", "咖啡", "热", "无糖", 15.0, 85, '["提神","经典","低卡","暖身"]', "热美式暖身更暖心，醇苦回甘适合冬日暖饮"),
    ("拿铁", "咖啡", "热/冰", "半糖", 18.0, 95, '["经典","奶香","柔和"]', "浓缩咖啡与牛奶的经典融合，口感柔和顺滑"),
    ("生椰拿铁", "咖啡", "冰", "半糖", 20.0, 92, '["椰香","清爽","热门"]', "瑞幸同款，椰乳搭配浓缩咖啡，东南亚风情"),
    ("厚乳拿铁", "咖啡", "热/冰", "微糖", 22.0, 88, '["浓郁","奶香","冬天"]', "加倍厚牛乳，口感浓郁醇厚"),
    ("澳白", "咖啡", "热", "无糖", 18.0, 75, '["精致","浓郁","短萃"]', "短萃取浓缩配丝滑奶泡，咖啡味更浓郁"),
    ("摩卡", "咖啡", "热/冰", "全糖", 20.0, 80, '["巧克力","甜蜜","甜点"]', "浓缩咖啡+巧克力酱+牛奶，甜蜜与咖啡的碰撞"),
    ("卡布奇诺", "咖啡", "热", "半糖", 18.0, 70, '["经典","奶泡","绵密"]', "浓厚奶泡配浓缩咖啡，口感绵密"),
    ("冷萃咖啡", "咖啡", "冰", "无糖", 18.0, 85, '["顺滑","低酸","提神"]', "12小时冷泡萃取，顺滑不酸涩"),
    ("陨石厚乳拿铁", "咖啡", "冰", "半糖", 23.0, 90, '["黑糖","挂壁","热门","新品"]', "黑糖挂壁+厚牛乳+浓缩咖啡，视觉与味觉双享受"),
    ("冰摇浓缩", "咖啡", "冰", "无糖", 16.0, 65, '["清爽","纯粹","小众"]', "浓缩咖啡加冰摇匀，简单纯粹"),
    ("茉莉绿茶", "纯茶", "热/冰", "无糖", 12.0, 75, '["花香","清新","低卡"]', "茉莉花香萦绕，清新淡雅"),
    ("乌龙茶", "纯茶", "热/冰", "无糖", 12.0, 70, '["焙火","回甘","传统"]', "炭焙乌龙，回甘悠长"),
    ("柠檬茶", "果茶", "冰", "半糖", 14.0, 82, '["清爽","维C","夏天"]', "现切柠檬配红茶底，清爽解暑"),
    ("满杯百香果", "果茶", "冰", "半糖", 16.0, 88, '["百香果","酸甜","夏天","热门"]', "百香果原浆+绿茶底，酸甜解腻"),
    ("桃桃乌龙", "果茶", "冰", "微糖", 17.0, 80, '["桃子","乌龙","清爽"]', "蜜桃果肉配乌龙茶底，清爽甘甜"),
    ("葡萄冰沙", "冰沙", "冰", "半糖", 18.0, 78, '["葡萄","冰沙","夏天"]', "葡萄果肉搅打冰沙，清凉解暑"),
    ("芒芒冰沙", "冰沙", "冰", "半糖", 18.0, 76, '["芒果","冰沙","夏天"]', "新鲜芒果冰沙，甜蜜浓郁"),
    ("珍珠奶茶", "奶茶", "热/冰", "全糖", 15.0, 90, '["经典","珍珠","甜蜜"]', "经典台式珍珠奶茶，Q弹嚼劲"),
    ("黑糖波波牛乳", "奶茶", "冰", "全糖", 19.0, 85, '["黑糖","珍珠","浓郁","热门"]', "黑糖挂壁+Q弹波波+牛乳，视觉系奶茶"),
    ("芋泥波波奶茶", "奶茶", "热/冰", "半糖", 20.0, 83, '["芋泥","波波","暖冬"]', "芋泥绵密配Q弹波波，冬天必点"),
    ("抹茶拿铁", "咖啡", "热/冰", "半糖", 19.0, 78, '["抹茶","清新","颜值"]', "日式抹茶配绵密奶泡，绿色观赏级"),
    ("椰青美式", "咖啡", "冰", "无糖", 19.0, 73, '["椰子","清爽","小众","低卡"]', "青椰水配浓缩咖啡，低卡清爽新选择"),
    ("鲜榨橙汁", "果蔬茶", "冰", "微糖", 15.0, 78, '["维C","鲜榨","健康","清爽"]', "鲜橙现榨，满满维C，自然清甜不加糖精"),
    ("羽衣甘蓝苹果汁", "果蔬茶", "冰", "无糖", 17.0, 65, '["绿色","排毒","健康","小众"]', "超级食物羽衣甘蓝+苹果慢榨，健康达人的选择"),
]


def init_db(db_path: str = None):
    """Initialize the beverages database with schema and seed data.

    Args:
        db_path: Path to the SQLite database file. Defaults to DB_PATH from config.
    """
    if db_path is None:
        db_path = DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.execute("DELETE FROM beverages")
    conn.executemany(
        "INSERT INTO beverages (name, category, temperature, sweetness, price, popularity, tags, description) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        SEED_DATA,
    )
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path} with {len(SEED_DATA)} beverages.")


if __name__ == "__main__":
    init_db()
