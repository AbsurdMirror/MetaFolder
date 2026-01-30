import sqlite3
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_db()
    
    def init_db(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # 创建文件/文件夹主表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relative_path TEXT UNIQUE,
            type TEXT,
            description TEXT
        )
        ''')
        
        # 创建标签表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        ''')
        
        # 创建关联表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS entry_tags (
            entry_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY(entry_id) REFERENCES entries(id),
            FOREIGN KEY(tag_id) REFERENCES tags(id),
            UNIQUE(entry_id, tag_id)
        )
        ''')
        
        # 创建索引以提高搜索性能
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_path ON entries(relative_path)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)')
        
        # 创建已扫描文件夹表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS scanned_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relative_path TEXT UNIQUE
        )
        ''')
        
        # 创建索引
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_scanned_folders_path ON scanned_folders(relative_path)')
        
        self.conn.commit()
    
    def add_entry(self, relative_path, entry_type, description=""):
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO entries (relative_path, type, description) VALUES (?, ?, ?)",
                (relative_path, entry_type, description)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"添加条目失败: {e}")
            return None
    
    def update_entry(self, relative_path, description):
        try:
            self.cursor.execute(
                "UPDATE entries SET description = ? WHERE relative_path = ?",
                (description, relative_path)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"更新条目失败: {e}")
            return False
    
    def get_entry(self, relative_path):
        try:
            self.cursor.execute(
                "SELECT id, type, description FROM entries WHERE relative_path = ?",
                (relative_path,)
            )
            return self.cursor.fetchone()
        except Exception as e:
            print(f"获取条目失败: {e}")
            return None
    
    def get_entries_by_path_prefix(self, path_prefix):
        try:
            if path_prefix == ".":
                # 获取根目录下的所有条目
                # 使用两种分隔符格式进行匹配，确保兼容Windows和其他系统
                self.cursor.execute(
                    "SELECT relative_path, type, description FROM entries WHERE relative_path NOT LIKE '%/%' AND relative_path NOT LIKE '%\\%'"
                )
            else:
                # 获取指定目录下的所有条目
                # 构建两种分隔符格式的前缀，确保兼容Windows和其他系统
                prefix_slash = f"{path_prefix}/"
                prefix_backslash = f"{path_prefix}\\"
                
                # 使用OR条件匹配两种路径格式
                self.cursor.execute(
                    "SELECT relative_path, type, description FROM entries WHERE (relative_path LIKE ? OR relative_path LIKE ?) AND (relative_path NOT LIKE ? AND relative_path NOT LIKE ?)",
                    (f"{prefix_slash}%", f"{prefix_backslash}%", f"{prefix_slash}%/%", f"{prefix_backslash}%\\%")
                )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"获取条目失败: {e}")
            return []
    
    def add_tag(self, tag_name):
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                (tag_name,)
            )
            self.conn.commit()
            # 获取标签ID
            self.cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            print(f"添加标签失败: {e}")
            return None
    
    def add_tag_to_entry(self, relative_path, tag_name):
        try:
            # 获取条目ID
            self.cursor.execute("SELECT id FROM entries WHERE relative_path = ?", (relative_path,))
            entry_id = self.cursor.fetchone()
            if not entry_id:
                return False
            entry_id = entry_id[0]
            
            # 添加标签并获取标签ID
            tag_id = self.add_tag(tag_name)
            if not tag_id:
                return False
            
            # 关联标签和条目
            self.cursor.execute(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                (entry_id, tag_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加标签到条目失败: {e}")
            return False
    
    def remove_tag_from_entry(self, relative_path, tag_name):
        try:
            # 获取条目ID
            self.cursor.execute("SELECT id FROM entries WHERE relative_path = ?", (relative_path,))
            entry_id = self.cursor.fetchone()
            if not entry_id:
                return False
            entry_id = entry_id[0]
            
            # 获取标签ID
            self.cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            tag_id = self.cursor.fetchone()
            if not tag_id:
                return False
            tag_id = tag_id[0]
            
            # 移除关联
            self.cursor.execute(
                "DELETE FROM entry_tags WHERE entry_id = ? AND tag_id = ?",
                (entry_id, tag_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"从条目移除标签失败: {e}")
            return False
    
    def get_tags_for_entry(self, relative_path):
        try:
            # 获取条目ID
            self.cursor.execute("SELECT id FROM entries WHERE relative_path = ?", (relative_path,))
            entry_id = self.cursor.fetchone()
            if not entry_id:
                return []
            entry_id = entry_id[0]
            
            # 获取标签
            self.cursor.execute('''
            SELECT tags.name FROM tags
            JOIN entry_tags ON tags.id = entry_tags.tag_id
            WHERE entry_tags.entry_id = ?
            ''', (entry_id,))
            return [tag[0] for tag in self.cursor.fetchall()]
        except Exception as e:
            print(f"获取条目标签失败: {e}")
            return []
    
    def search_entries(self, query, search_type="all"):
        try:
            if search_type == "tag":
                # 按标签搜索
                self.cursor.execute('''
                SELECT entries.relative_path, entries.type, entries.description FROM entries
                JOIN entry_tags ON entries.id = entry_tags.entry_id
                JOIN tags ON entry_tags.tag_id = tags.id
                WHERE tags.name LIKE ?
                ''', (f"%{query}%",))
            elif search_type == "description":
                # 按备注搜索
                self.cursor.execute(
                    "SELECT relative_path, type, description FROM entries WHERE description LIKE ?",
                    (f"%{query}%",)
                )
            elif search_type == "name":
                # 按文件名搜索
                self.cursor.execute(
                    "SELECT relative_path, type, description FROM entries WHERE relative_path LIKE ?",
                    (f"%{query}%",)
                )
            else:
                # 综合搜索
                self.cursor.execute('''
                SELECT DISTINCT entries.relative_path, entries.type, entries.description FROM entries
                LEFT JOIN entry_tags ON entries.id = entry_tags.entry_id
                LEFT JOIN tags ON entry_tags.tag_id = tags.id
                WHERE entries.relative_path LIKE ? OR entries.description LIKE ? OR tags.name LIKE ?
                ''', (f"%{query}%", f"%{query}%", f"%{query}%"))
            
            return self.cursor.fetchall()
        except Exception as e:
            print(f"搜索条目失败: {e}")
            return []
    
    def add_scanned_folder(self, relative_path):
        """添加已扫描文件夹"""
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO scanned_folders (relative_path) VALUES (?)",
                (relative_path,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加已扫描文件夹失败: {e}")
            return False
    
    def is_folder_scanned(self, relative_path):
        """检查文件夹是否已扫描"""
        try:
            self.cursor.execute(
                "SELECT id FROM scanned_folders WHERE relative_path = ?",
                (relative_path,)
            )
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"检查文件夹是否已扫描失败: {e}")
            return False
    
    def get_scanned_folders(self):
        """获取所有已扫描文件夹"""
        try:
            self.cursor.execute("SELECT relative_path FROM scanned_folders")
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"获取已扫描文件夹失败: {e}")
            return []
    
    def remove_scanned_folder(self, relative_path):
        """移除已扫描文件夹"""
        try:
            self.cursor.execute(
                "DELETE FROM scanned_folders WHERE relative_path = ?",
                (relative_path,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"移除已扫描文件夹失败: {e}")
            return False
    
    def close(self):
        if self.conn:
            self.conn.close()