#!/usr/bin/env python3

import tempfile
import os
from pathlib import Path
from db import DatabaseManager
from scanner import FileScanner

def test_database_initialization():
    """测试数据库初始化"""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "metadata.db")
        db_manager = DatabaseManager(db_path)
        
        # 验证数据库文件是否创建
        assert os.path.exists(db_path), "数据库文件未创建"
        
        # 验证表是否创建
        cursor = db_manager.conn.cursor()
        
        # 检查entries表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        assert cursor.fetchone() is not None, "entries表未创建"
        
        # 检查tags表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags'")
        assert cursor.fetchone() is not None, "tags表未创建"
        
        # 检查entry_tags表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entry_tags'")
        assert cursor.fetchone() is not None, "entry_tags表未创建"
        
        db_manager.close()
        print("数据库初始化测试通过")

def test_file_scanner():
    """测试文件扫描"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件和文件夹
        os.makedirs(os.path.join(temp_dir, "subfolder"))
        with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
            f.write("test1")
        with open(os.path.join(temp_dir, "subfolder", "file2.txt"), "w") as f:
            f.write("test2")
        
        # 初始化数据库和扫描器
        db_path = os.path.join(temp_dir, "metadata.db")
        db_manager = DatabaseManager(db_path)
        scanner = FileScanner(Path(temp_dir), db_manager)
        
        # 扫描文件
        scanner.scan()
        
        # 打印所有扫描到的条目
        print("\n扫描到的条目:")
        cursor = db_manager.conn.cursor()
        cursor.execute("SELECT relative_path, type FROM entries")
        for row in cursor.fetchall():
            print(f"  {row[0]} ({row[1]})")
        
        # 验证文件是否被扫描到
        
        # 检查根目录下的文件
        cursor.execute("SELECT relative_path FROM entries WHERE relative_path = 'file1.txt'")
        assert cursor.fetchone() is not None, "file1.txt未被扫描到"
        print("file1.txt 扫描到")
        
        # 检查子文件夹
        cursor.execute("SELECT relative_path FROM entries WHERE relative_path = 'subfolder'")
        assert cursor.fetchone() is not None, "subfolder未被扫描到"
        print("subfolder 扫描到")
        
        # 检查子文件夹下的文件
        cursor.execute("SELECT relative_path FROM entries WHERE relative_path = 'subfolder\\file2.txt'")
        result = cursor.fetchone()
        if result is None:
            # 尝试使用正斜杠
            cursor.execute("SELECT relative_path FROM entries WHERE relative_path = 'subfolder/file2.txt'")
            result = cursor.fetchone()
        assert result is not None, "subfolder/file2.txt未被扫描到"
        print("subfolder/file2.txt 扫描到")
        
        db_manager.close()
        print("文件扫描测试通过")

if __name__ == "__main__":
    test_database_initialization()
    test_file_scanner()
    print("所有测试通过！")