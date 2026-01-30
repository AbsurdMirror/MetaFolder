import os
from pathlib import Path

class FileScanner:
    def __init__(self, root_dir, db_manager):
        self.root_dir = root_dir
        self.db_manager = db_manager
    
    def scan(self, progress_callback=None):
        """递归扫描目录并将文件和文件夹信息添加到数据库"""
        total_items = 0
        processed_items = 0
        
        # 先计算总项目数
        for root, dirs, files in os.walk(self.root_dir):
            total_items += len(dirs) + len(files)
        
        # 开始扫描
        for root, dirs, files in os.walk(self.root_dir):
            # 处理当前目录
            current_path = Path(root)
            relative_path = current_path.relative_to(self.root_dir)
            if relative_path == Path('.'):
                relative_path_str = '.'
            else:
                relative_path_str = str(relative_path)
            
            # 添加目录到数据库
            if relative_path_str != '.':
                self.db_manager.add_entry(relative_path_str, 'folder')
                processed_items += 1
                if progress_callback:
                    progress_callback(processed_items, total_items, f"扫描目录: {relative_path_str}")
            
            # 处理当前目录下的文件
            for file in files:
                # 跳过数据库文件本身
                if file == 'metadata.db':
                    continue
                
                file_path = current_path / file
                file_relative_path = file_path.relative_to(self.root_dir)
                file_relative_path_str = str(file_relative_path)
                self.db_manager.add_entry(file_relative_path_str, 'file')
                processed_items += 1
                if progress_callback:
                    progress_callback(processed_items, total_items, f"扫描文件: {file_relative_path_str}")
    
    def scan_current_level(self, relative_path, progress_callback=None):
        """扫描指定相对路径目录的下一层内容"""
        # 获取绝对路径
        if relative_path == '.':
            absolute_path = self.root_dir
        else:
            absolute_path = self.root_dir / Path(relative_path)
        
        # 验证路径是否存在且是目录
        if not absolute_path.exists() or not absolute_path.is_dir():
            return
        
        # 获取目录下的所有项目
        items = []
        try:
            items = list(absolute_path.iterdir())
        except Exception as e:
            print(f"扫描目录失败: {e}")
            return
        
        # 开始扫描
        total_items = len(items)
        processed_items = 0
        
        for item in items:
            # 计算相对路径
            item_relative_path = item.relative_to(self.root_dir)
            item_relative_path_str = str(item_relative_path)
            
            # 跳过数据库文件
            if item.name == 'metadata.db':
                processed_items += 1
                if progress_callback:
                    progress_callback(processed_items, total_items, f"跳过数据库文件")
                continue
            
            # 判断是文件还是文件夹
            if item.is_dir():
                self.db_manager.add_entry(item_relative_path_str, 'folder')
                if progress_callback:
                    progress_callback(processed_items, total_items, f"扫描目录: {item.name}")
            else:
                self.db_manager.add_entry(item_relative_path_str, 'file')
                if progress_callback:
                    progress_callback(processed_items, total_items, f"扫描文件: {item.name}")
            
            processed_items += 1
    
    def get_absolute_path(self, relative_path):
        """根据相对路径获取绝对路径"""
        if relative_path == '.':
            return self.root_dir
        return self.root_dir / Path(relative_path)