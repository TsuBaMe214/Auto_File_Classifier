#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created: 2025-10-17

"""
@Author: Swallow Du (https://github.com/TsuBaMe214)
Updated: 2025-10-17
Description: This tool is used to classify files.
            You can classify your files by file extension or by EXIF info (for photographers).
            Adjustable parameters can be controlled via config.json.
Version: 1.0.0

功能说明:
    - 对路径下文件按照文件类型（文件拓展名）进行分类
    - 针对摄影师/图像工作者，可以根据EXIF信息进行分类
    - 参数由config.json控制
"""
import os
import shutil
import time
import exifread
import json


class ConfigManager:
    def __init__(self):
        self.config_path = os.path.join(os.getcwd(), "config.json")
        self.default_config = {
            "target_path": "",
            "classify_by_ext": True,
            "exif_mode": ""
        }
        self.config = {}
        self.load()

    def load(self):
        """
        用于读取参数文件(固定路径为程序所在同级目录下，命名为config.json)，如果未检测到则自动生成默认参数文件。然后从参数文件中读取参数。
        """
        # 当json配置文件不存在时，自动根据default_config创建
        if not os.path.exists(self.config_path):
            self.create_default_config()
        # 读取文件
        with open(self.config_path, "r", encoding="utf-8") as f:
            # 先以文本形式，去掉以#开头的行
            lines = [line for line in f if not line.strip().startswith("#")]
            # 对可能出现的路径斜杠问题修正
            json_text = "".join(lines)
            json_text = json_text.replace("\\", "/")

            # 对剩下的行进行json格式读取
            config = json.loads(json_text)

            # 如果target_path为空，需要用户手动input传入(同时会进行路径判断)
            while not config["target_path"] or not os.path.exists(config["target_path"]):
                config["target_path"] = input(f"Enter Target Path(Since Config Setting Empty):")

            # 将config信息传入类结构中
            self.config = config

    def create_default_config(self):
        """
        用于创建默认参数配置文件，特别是当初次使用或使用过程中误删config文件后，可以自动生成初始化配置文件
        """

        help_text = (
        '# 说明([]内为可选参数，用 | 分隔)：\n'
        '# target_path：需要分类的素材所在路径，支持子文件夹\n'
        '# classify_by_ext：是否按拓展名分类(同时启用拓展名分类和EXIF分类时，优先进行EXIF分类，如"拍摄时间-Raw|JPG"层级) [True | False]\n'
        '# exif_mode：EXIF分类方式，支持按相机、拍摄日期分类(根据作者实际经验，该两项相对常用) [0:相机机型 | 1:拍摄日期 | "":不进行EXIF分类]\n'
        )
        # 以w方式打开json文件(固定为程序所在同级目录下，命名为config.json)
        with open(self.config_path, "w", encoding="utf-8") as f:
            # 写入提示帮助信息
            f.write(help_text)
            # 将default内容dump到json文件中
            json.dump(self.default_config, f, indent=4, ensure_ascii=False)
        # 提示未检测到config文件，自动生成默认config文件
        print(f"\tNo Config FIle Found.\nDefault Config created at : [{self.config_path}]")

class ImageInfo:
    def __init__(self):
        self.target_path = r""
        self.exif_dic = {}
        self.file_info = {}
        self.exif_classify_mode = ""
        self.is_ext_classify = True

    def get_file_info(self):
        """
        获取指定路径下所有文件的信息，包括文件名、拓展名、路径、所在文件夹
        """
        # 遍历路径并获取所有文件名及后缀
        for root, dirs, files in os.walk(self.target_path):
            for file in files:
                # 分割文件名及拓展名
                file_name, file_expand_name = os.path.splitext(file)
                # 如果读取到文件名的情况下，将拓展名、路径等信息作为子字典，更新到类中
                if file_expand_name:
                    info = {"Name": file_name,
                            "ext": file_expand_name.replace(".", ""),
                            "Path": os.path.join(root, file),
                            "Folder": root}
                    self.file_info[file] = info
                    # 将info初始化为空字典，避免覆写
                    info = {}

    def classify_expand_name(self):
        """
        遍历文件并逐一进行文件名、拓展名的拆分，同时在原有路径下对文件按拓展名进行文件夹分类。
        """
        for file in self.file_info:
            type_folder = os.path.join(self.file_info[file]["Folder"], str(self.file_info[file]["ext"]))
            os.makedirs(type_folder, exist_ok=True)
            # 拼接原始路径
            file_original_path = str(self.file_info[file]["Path"])
            # 拼接分类文件夹路径
            file_new_path = os.path.join(type_folder, file)
            # 尝试移动文件
            try:
                shutil.move(file_original_path, file_new_path)
                print(f"Try to Move File [{file}]...\n\tFrom [{file_original_path}] -> [{file_new_path}]")
                # 同时将文件路径更新到file_info中
                self.file_info[file]["Path"] = file_new_path
            except Exception as e:
                print(f"Failed to Move File [{file}] : {e}")
                pass

    def get_exif_metadata(self):
        """
        获取图片的exif信息，支持场景raw格式。并将读取得到的内容保存在exif_dic中。
        包括文件类型、日期、拍摄时间、相机型号、ISO、曝光时间、光圈信息。
        """
        # 遍历文件
        for file in self.file_info:
            # 跳开同名文件，避免重复读取
            if self.file_info[file]["Name"] not in self.exif_dic:
                # 使用exifread读取exif信息
                with open(self.file_info[file]["Path"], 'rb') as img:
                    tags = exifread.process_file(img, details=False)
                    # 将以下内容存储（暂列常用属性如曝光、光圈、ISO等）
                    file_exif = {"Type": f"{self.file_info[file]['ext']}",
                                 "Date": tags.get('EXIF DateTimeOriginal').printable.split(" ")[0].replace(":", "-"),
                                 "Time": tags.get('EXIF DateTimeOriginal').printable.split(" ")[-1],
                                 "CameraModel": tags.get('Image Model').printable,
                                 "ISO": "ISO" + tags.get('EXIF ISOSpeedRatings').printable,
                                 "Shutter": tags.get('EXIF ExposureTime').printable + "s",
                                 "Aperture": "f" + tags.get('EXIF FNumber').printable}
                    # 将exif信息更新到实例中
                    self.exif_dic[self.file_info[file]["Name"]] = file_exif
                    # 将临时的file_exif字典清空，避免覆写
                    file_exif = {}

    def classify_exif(self):
        """
        按照exif信息进行文件的分类，按照个人使用习惯，目前仅提供按相机型号、拍摄日期进行分类
        """
        # 选择通过EXIF控制分组，0:按相机型号分类 | 1:按拍摄日期分类
        if self.exif_classify_mode:
            print(f"Select Mode [{self.exif_classify_mode}]")
        else:
            return

        # 遍历文件
        for file in self.file_info:
            # 文件名
            file_name = os.path.splitext(file)[0]
            # 仅当文件名含有对应的exif信息时操作
            if file_name in self.exif_dic:
                # 获取文件所在路径
                original_path = self.file_info[file]["Path"]
                root_path = os.path.dirname(original_path)
                # 根据相机型号分类
                if self.exif_classify_mode == "0":
                    # 读取对应文件的相机型号
                    camera_model = self.exif_dic[file_name]["CameraModel"]
                    # 设置目标存放新文件夹路径
                    dst_folder = str(os.path.join(root_path, camera_model))

                # 根据拍摄日期进行分类
                elif self.exif_classify_mode == "1":
                    # 读取拍摄日期
                    capture_date = self.exif_dic[file_name]["Date"]
                    # 设置目标存放新文件夹路径
                    dst_folder = str(os.path.join(root_path, capture_date))

                # 不进行exif分类，直接结束函数
                elif self.exif_classify_mode == "":
                    print(f"Skip EXIF Classify.")
                    return

                # 用户设置其他模式
                else:
                    print(f"Unsupported Mode : [{self.exif_classify_mode}].")
                    raise

                # 创建目标文件夹
                os.makedirs(dst_folder, exist_ok=True)
                # 设置移动目标路径
                dst_path = os.path.join(dst_folder, file)
                # 对文件进行移动
                try:
                    shutil.move(original_path, dst_path)
                    print(f"Try to Move File [{file}]...\n\tFrom [{original_path}] -> [{dst_path}]")
                    # 更新文件路径到file_info中
                    self.file_info[file]["Path"] = dst_path
                    self.file_info[file]["Folder"] = dst_folder
                # 设置异常提示
                except FileExistsError:
                    print(f"File [{file}] already Exist in Folder [{camera_model_folder}]!")
                except PermissionError:
                    print(f"No Permission Access or Write!")
                except FileNotFoundError:
                    print(f"Source File [{file}] not Exists!")


def main():
    """
    主函数，负责调用各种函数进行分类操作
    """
    # 分别创建ConfigManager与ImageInfo类的实例
    configmanager = ConfigManager()
    image_info = ImageInfo()
    # 读取target_path及需要分类的素材文件路径
    image_info.target_path = configmanager.config["target_path"]
    # 更新exif分类模式
    image_info.exif_classify_mode = configmanager.config["exif_mode"]
    # 判断是否需要exif分类
    image_info.is_ext_classify = configmanager.config["classify_by_ext"]
    # 读取文件及EXIF信息
    image_info.get_file_info()
    image_info.get_exif_metadata()
    # 进行分类操作，优先exif分类
    image_info.classify_exif()
    image_info.classify_expand_name()
    print(f"Finished Classify!")


if __name__ == "__main__":
    print(__doc__)
    main()
    print(f"\n\nProgram will be exited in 5 Seconds.")
    time.sleep(5)
