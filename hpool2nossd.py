#!/usr/bin/env python3
# coding=utf-8

'''
@File  : hpool2nossd.py
@author: liuyuansharp
@Time  : 2023/01/10 21:23
'''
import os
import sys
import subprocess
import shutil
import stat
from time import sleep

from pathlib import Path
from typing import Dict
from ruamel.yaml import YAML

class DriveInfo():
    def __init__(self) -> None:
        self.drive_path: Path = Path()

        self.nossd_path: Path = Path()
        self.tmp_drive_flag = False
        self.fpts_n = 0
        self.spts_n = 0

        self.target_use_space = 0
        self.target_fpts_n = 0
        self.target_spts_n = 0

        self.plots_path: Path = Path()
        self.plots_n = 0

        self.total_gb = 0
        self.used_gb = 0
        self.free_gb = 10000000

        self.plotting_flag = False
        self.finalizing_flag = False


class hpool2nossd():
    def __init__(self,config_yaml) -> None:

        ################### 配置区域开始###################
        # 是否fpt文件优先
        self.fpt_priority = False
        # 每次删除hpool图数量
        self.delete_plots_num_per_time = 2

        # 磁盘挂载根目录
        self.drive_root_path = Path("/srv/")
        # 磁盘文件夹标识（用于排除磁盘挂载根目录下排除无效目录，可为填""，则不作排除）
        self.drive_character = "disk"

        # hpool图目录名
        self.plots_dir = "chiapp-files"
        # nossd图目录名
        self.nossd_dir = "nossd"
        # hpool服务名
        self.hpool_service = "hpoolpp"
        # nossd服务名
        self.nossd_service = "nossd"

        # nossd安装文件目录
        self.nossd_path = Path("/root/install/nossd-1.2/")
        # nossd脚本名
        self.nossd_start_sh_name = "start.sh"

        # nossd压缩等级
        self.nossd_type = 5
        # nossd机器名
        self.nossd_name = "bsh_001"
        # nossd收益地址
        self.nossd_address = "xch1m49h6ny95xgs5a3p2wg6ghnr3vejsqq2pwklq9ae8kg8wgkfujcs26djuq"
        # nossd临时文件磁盘
        self.nossd_tmp_drive_paths = \
            [
                "/srv/dev-disk-by-uuid-9802c526-c5e2-44a4-9e29-b7e1b7b805a0",
                "/srv/dev-disk-by-uuid-ffeb0e19-8f2a-453a-abec-9aa7884c1124",
                "/srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01"
            ]

        # 等待检查间隔(s)
        self.waitting_time = 300
        ################### 配置区域结束####################

        self.spt_space = [96.1, 94.1, 92.1, 90.1,
                          88.1][self.nossd_type - 1]  # gb
        self.fpt_space = [84.5, 82.9, 81.3, 79.7,
                          78.1][self.nossd_type - 1]  # gb

        self.total_tmp_space = 225
        self.nossd_client = self.nossd_path / "client"
        self.nossd_start_sh = self.nossd_path / self.nossd_start_sh_name

        self.all_dirves: Dict[Path, DriveInfo] = {}

        self.readonly_drives: Dict[Path, DriveInfo] = {}
        self.tmp_spt_or_fpt_drives: Dict[Path, DriveInfo] = {}
        self.spt_or_fpt_drives: Dict[Path, DriveInfo] = {}

        self.plotting_drives: Dict[Path, DriveInfo] = {}
        self.finalizing_drives: Dict[Path, DriveInfo] = {}

        self.debug = True

        self.all_plots = 0
        self.all_spts = 0
        self.all_fpts = 0
        self.all_space = 0

        self.config_yaml = config_yaml
        
    def load_config_yaml(self):
        yaml = YAML(typ='safe')
        with open(self.config_yaml, encoding='utf-8') as file:
            data = yaml.load(file)
            if "fpt_priority" in data:
                self.fpt_priority = data["fpt_priority"]
            
            if "delete_plots_num_per_time" in data:
                self.delete_plots_num_per_time = data["delete_plots_num_per_time"]
                
            if "drive_root_path" in data:
                self.drive_root_path = Path(data["drive_root_path"])
                
            if "drive_character" in data:
                self.drive_character = data["drive_character"]
                
            if "plots_dir" in data:
                self.plots_dir = data["plots_dir"]
                
            if "nossd_dir" in data:
                self.nossd_dir = data["nossd_dir"]
                
            if "hpool_service" in data:
                self.hpool_service = data["hpool_service"]
                
            if "nossd_service" in data:
                self.nossd_service = data["nossd_service"]
                
            if "nossd_path" in data:
                self.nossd_path = Path(data["nossd_path"])
                
            if "nossd_start_sh" in data:
                self.nossd_start_sh_name = data["nossd_start_sh"]
                
            if "nossd_type" in data:
                self.nossd_type = data["nossd_type"]
                
            if "nossd_name" in data:
                self.nossd_name = data["nossd_name"]
                
            if "nossd_address" in data:
                self.nossd_address = data["nossd_address"]
                
            if "nossd_tmp_drive_paths" in data:
                self.nossd_tmp_drive_paths = data["nossd_tmp_drive_paths"]
                
            if "nossd_service" in data:
                self.nossd_service = data["nossd_service"]    
                
            if "waitting_time" in data:
                self.waitting_time = data["waitting_time"]        
                
    def reduce_plots(self):
        deleted_num = 0
        need_to_delete_num = self.delete_plots_num_per_time

        for d in self.tmp_spt_or_fpt_drives:
            drive_info = self.tmp_spt_or_fpt_drives[d]

            n = 1
            if drive_info.plots_n >= need_to_delete_num:
                n = need_to_delete_num
            else:
                n = drive_info.plots_n

            self.delete_plots(drive_info.plots_path, n)
            deleted_num += n
            need_to_delete_num -= n
            drive_info.plots_n -= n
            self.print_drive_info("deleted", drive_info)

            if need_to_delete_num == 0:
                return

        for d in self.spt_or_fpt_drives:
            drive_info = self.spt_or_fpt_drives[d]

            n = 1
            if drive_info.plots_n >= need_to_delete_num:
                n = need_to_delete_num
            else:
                n = drive_info.plots_n

            self.delete_plots(drive_info.plots_path, n)
            deleted_num += n
            need_to_delete_num -= n
            drive_info.plots_n -= n
            self.print_drive_info("deleted", drive_info)

            if need_to_delete_num == 0:
                return

    @staticmethod
    def delete_plots(plots_path: Path, n: int):
        count = 1
        if plots_path.exists():
            plots = os.listdir(plots_path)
            for p in plots:
                plot = os.path.join(plots_path, p)

                print("deleting " + plot + "...")
                if os.path.exists(plot):
                    os.remove(plot)
                    count += 1
                print("done " + plot + "...\n")

                if count > n:
                    print("done, deleted {} plots in {}!\n".format(n, plots_path))
                    return

    def is_all_drives_plots_empty(self):
        count = 0
        for d in self.all_dirves:
            count += self.all_dirves[d].plots_n

        if count == 0:
            return True

        return False

    def set_hpool_service(self, cmd):
        p = subprocess.Popen("service {} {}".format(self.hpool_service, cmd),
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
            return True

        return False

    def set_nossd_service(self, cmd):
        p = subprocess.Popen("service {} {}".format(self.nossd_service, cmd),
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
            return True

        return False

    def get_drive_info(self, drive_path: Path) -> DriveInfo:

        d = DriveInfo()

        gb = 1024 ** 3  # GB == gigabyte
        total_b, used_b, free_b = shutil.disk_usage(drive_path)

        d.drive_path = drive_path

        d.total_gb = int(total_b/gb)
        d.used_gb = int(used_b/gb)
        d.free_gb = int(free_b/gb)

        nossd_path = drive_path / self.nossd_dir
        fpts_n = spts_n = plotting_n = 0
        if nossd_path.exists():
            fpts_n = self.get_type_file_number(nossd_path, ".fpt")
            spts_n = self.get_type_file_number(nossd_path, ".spt")
            plotting_n = self.get_type_file_number(nossd_path, ".spt_part")
            finalizing_n = self.get_type_file_number(nossd_path, ".fpt_part")

            if plotting_n:
                d.plotting_flag = True

            if finalizing_n:
                d.finalizing_flag = True

        d.nossd_path = nossd_path
        d.fpts_n = fpts_n
        d.spts_n = spts_n

        nossd_space = d.total_gb
        if str(drive_path) in self.nossd_tmp_drive_paths:
            d.tmp_drive_flag = True
            nossd_space -= self.total_tmp_space / \
                len(self.nossd_tmp_drive_paths)

        if nossd_space > 0:
            d.target_use_space = int(nossd_space)
            d.target_spts_n = int(nossd_space // self.spt_space)
            d.target_fpts_n = int(nossd_space // self.fpt_space)

        plots_path = drive_path / self.plots_dir
        plots_n = 0
        if plots_path.exists():
            d.plots_path = plots_path
            plots_n = self.get_type_file_number(plots_path, ".plot")

        d.plots_n = plots_n

        return d

    def get_all_dirves(self):
        dirs = os.listdir(self.drive_root_path)
        
        all_plots = 0
        all_spts = 0
        all_fpts = 0
        all_space = 0
        for drive_dir in dirs:
            drive_dir_path = self.drive_root_path / drive_dir
            drive_info = self.get_drive_info(drive_dir_path)

            if self.drive_character:
                if self.drive_character in drive_dir:
                    self.all_dirves[drive_dir_path] = drive_info
                    all_plots += drive_info.plots_n
                    all_spts += drive_info.spts_n
                    all_fpts += drive_info.fpts_n
                    all_space += drive_info.total_gb
            else:
                self.all_dirves[drive_dir_path] = drive_info
                all_plots += drive_info.plots_n
                all_spts += drive_info.spts_n
                all_fpts += drive_info.fpts_n
                all_space += drive_info.total_gb
        
        self.all_plots = all_plots
        self.all_spts = all_spts
        self.all_fpts = all_fpts
        self.all_space = all_space
        
        return self.all_dirves

    @staticmethod
    def get_type_file_number(dir, type):
        files = os.listdir(dir)
        no = 0
        for file in files:
            if type in file:
                no += 1

        return no

    def print_drive_info(self, status, d: DriveInfo) -> None:
        print("\nstatus: {}, {:.2f}%".format(status,(self.all_space - self.all_plots*101.3)*100/self.all_space))

        print("drive:  {}".format(d.drive_path))
        print(
            "space:     [total/used/free] : [{}/{}/{}]".format(d.total_gb, d.used_gb, d.free_gb))
        print(
            "info:      [plots/fpts/spts] : [{}/{}/{}]".format(d.plots_n,d.fpts_n, d.spts_n))
        
        all = len(self.all_dirves)
        completed = len(self.readonly_drives)
        uncompleted = len(self.all_dirves) - len(self.readonly_drives)
        print("space_all: [all/comp/uncomp] : [{}/{}/{}]".format(all,completed,uncompleted))
        print("info_all : [plots/fpts/spts] : [{}/{}/{}]".format(self.all_plots,self.all_fpts,self.all_spts))

        sys.stdout.flush()

    def is_completed_drive(self, d: DriveInfo) -> bool:

        condition = d.fpts_n >= d.target_fpts_n

        if not d.plotting_flag and not d.finalizing_flag and condition:
            # self.print_drive_info("completed", d)
            return True

        return False

    def is_plotting_drive(self, d: DriveInfo) -> bool:

        if d.plotting_flag:
            # self.print_drive_info("plotting", d)
            return True

        return False

    def is_finalizing_drive(self, d: DriveInfo) -> bool:

        if d.finalizing_flag:
            # self.print_drive_info("finalizing", d)
            return True

        return False

    def is_tmp_drive(self, d: DriveInfo) -> bool:

        if d.tmp_drive_flag:
            # self.print_drive_info("tmp_drive", d)
            return True

        return False

    def get_drives_status(self):

        self.readonly_drives.clear()
        self.tmp_spt_or_fpt_drives.clear()
        self.spt_or_fpt_drives.clear()
        self.plotting_drives.clear()
        self.finalizing_drives.clear()

        for drive in self.all_dirves:

            drive_info = self.all_dirves[drive]

            if self.is_completed_drive(drive_info):  # 已完成磁盘
                self.readonly_drives[drive] = drive_info
            elif self.is_tmp_drive(drive_info):  # 临时文件磁盘
                self.tmp_spt_or_fpt_drives[drive] = drive_info
            else:  # 其余转换磁盘
                self.spt_or_fpt_drives[drive] = drive_info

            if self.is_plotting_drive(drive_info):  # 正在转换spt
                self.plotting_drives[drive] = drive_info

            if self.is_finalizing_drive(drive_info):  # 正在转换fpt
                self.finalizing_drives[drive] = drive_info
                
        for d in self.plotting_drives:
            self.print_drive_info("plotting", self.plotting_drives[d])
            
        for d in self.finalizing_drives:
            self.print_drive_info("finalizing", self.plotting_drives[d])
            
    def update_nossd_start_sh(self, fpt_priority):
        start_sh_context = '#!/usr/bin/env bash \n'\
                           'cd \"$(dirname \"$(realpath \"${BASH_SOURCE[0]:-$0}\")\")\"\n'
        start_sh_context += str(self.nossd_client) + " \\" + "\n"
        start_sh_context += "	" + " -a " + \
            str(self.nossd_address) + " \\" + "\n"
        start_sh_context += "	" + " -c " + \
            str(self.nossd_type) + " -w " + \
            str(self.nossd_name) + " --no-benchmark \\" + "\n"

        for d in self.tmp_spt_or_fpt_drives:
            drive_info = self.tmp_spt_or_fpt_drives[d]

            nossd_dir = drive_info.drive_path / self.nossd_dir
            if not nossd_dir.exists():
                nossd_dir.mkdir()

            if fpt_priority:
                start_sh_context += "	 -d,{:d}GB,{:d}N,tsf {} \\".format(
                    drive_info.target_use_space, drive_info.target_fpts_n, nossd_dir) + "\n"
            else:
                start_sh_context += "	 -d,{:d}GB,{:d}N,ts {} \\".format(
                    drive_info.target_use_space, drive_info.target_spts_n, nossd_dir) + "\n"

        for d in self.spt_or_fpt_drives:
            drive_info = self.spt_or_fpt_drives[d]

            nossd_dir = drive_info.drive_path / self.nossd_dir
            if not nossd_dir.exists():
                nossd_dir.mkdir()

            if fpt_priority:
                start_sh_context += "	 -d,{:d}GB,{:d}N,sf {} \\".format(
                    drive_info.target_use_space, drive_info.target_fpts_n, nossd_dir) + "\n"
            else:
                start_sh_context += "	 -d,{:d}GB,{:d}N,s {} \\".format(
                    drive_info.target_use_space, drive_info.target_spts_n, nossd_dir) + "\n"

        for d in self.readonly_drives:
            drive_info = self.readonly_drives[d]

            nossd_dir = drive_info.drive_path / self.nossd_dir
            if not nossd_dir.exists():
                nossd_dir.mkdir()

            start_sh_context += "	 -d,r {} \\".format(nossd_dir) + "\n"

        with open(self.nossd_start_sh, "w") as f:
            f.write(start_sh_context)
            f.close()

            os.chmod(self.nossd_start_sh, stat.S_IRWXU)

    def run(self):
        
        self.load_config_yaml()
        
        # 获取初始磁盘信息
        self.get_all_dirves()
        # 更新磁盘状态
        self.get_drives_status()

        if len(self.plotting_drives) == 0 and len(self.finalizing_drives) == 0:
            if not self.is_all_drives_plots_empty():
                # 重启nossd，更新nossd脚本
                if self.set_nossd_service("stop"):
                    self.update_nossd_start_sh(self.fpt_priority)
                    self.set_nossd_service("start")
            else:
                if not self.fpt_priority:
                    print("spts -> fpts....\n")
                    # 重启nossd，更新nossd脚本
                    if self.set_nossd_service("stop"):
                        self.update_nossd_start_sh(True)
                        self.set_nossd_service("start")
                else:
                    print("done")
                    return

        while True:
            print("waitting {} s ,check drives status again....\n".format(
                self.waitting_time))
            sys.stdout.flush()
            sleep(self.waitting_time)  # 5 min

            # 更新磁盘状态
            print("check drives status....\n")
            sys.stdout.flush()

            # 更新磁盘信息
            self.get_all_dirves()
            # 更新磁盘状态
            self.get_drives_status()

            if len(self.plotting_drives) == 0 and len(self.finalizing_drives) == 0:
                # 再次确认,避免Nossd完成上一张图切换下一张图时进入删图流程
                sleep(300)
                # 更新磁盘信息
                self.get_all_dirves()
                # 更新磁盘状态
                self.get_drives_status()
                if len(self.plotting_drives) == 0 and len(self.finalizing_drives) == 0:
                    if not self.is_all_drives_plots_empty():
                        # 重启hpool，删除plots
                        if self.set_hpool_service("stop"):
                            self.reduce_plots()
                            self.set_hpool_service("start")

                        # 重启nossd，更新nossd脚本
                        if self.set_nossd_service("stop"):
                            self.update_nossd_start_sh(self.fpt_priority)
                            self.set_nossd_service("start")
                    else:
                        if not self.fpt_priority:
                            print("spts -> fpts....\n")
                            # 重启nossd，更新nossd脚本
                            if self.set_nossd_service("stop"):
                                self.update_nossd_start_sh(True)
                                self.set_nossd_service("start")
                        else:
                            print("done")
                            return


if __name__ == '__main__':

    config_yaml = "./config.yaml"
    if len(sys.argv) > 1:
        config_yaml = sys.argv[1]

    n = hpool2nossd(config_yaml)
    n.run()
