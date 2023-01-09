import os
import subprocess
import shutil
import stat

from pathlib import Path
from typing import Dict


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


class Hpool2Nossd():
    def __init__(self) -> None:

        self.fpt_priority = True
        self.parallel_nossd_num = 3
        self.delete_plot_per_time = 1

        self.total_tmp_space = 225
        self.min_free_space = 80  # gb
        self.spt_space = 88.1  # gb
        self.fpt_space = 78.1  # gb

        self.drive_root_path = Path("/srv/")
        self.drive_character = "disk"

        self.plots_dir = "chiapp-files"
        self.nossd_dir = "nossd"

        self.nossd_client_path = Path("/root/install/nossd-1.2/")
        self.nossd_client_client = self.nossd_client_path / "client"
        self.nossd_client_start_sh = self.nossd_client_path / "start_dev.sh"
        self.tmp_drive_paths = ["/srv/dev-disk-by-uuid-9802c526-c5e2-44a4-9e29-b7e1b7b805a0",
                               "/srv/dev-disk-by-uuid-ffeb0e19-8f2a-453a-abec-9aa7884c1124",
                               "/srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01"]
        self.nossd_client_address = "xch1m49h6ny95xgs5a3p2wg6ghnr3vejsqq2pwklq9ae8kg8wgkfujcs26djuq"
        self.nossd_client_type = 5
        self.nossd_client_name = "bsh_002"

        self.all_dirves: Dict[Path, DriveInfo] = {}

        self.readonly_drives: Dict[Path, DriveInfo] = {}
        self.tmp_spt_or_fpt_drives: Dict[Path, DriveInfo] = {}
        self.spt_or_fpt_drives: Dict[Path, DriveInfo] = {}

        self.plotting_drives: Dict[Path, DriveInfo] = {}
        self.finalizing_drives: Dict[Path, DriveInfo] = {}
        

        self.debug = True

    @staticmethod
    def delete_plots(hard, n):
        count = 1
        file = os.listdir(hard)

        print("delete " + hard + "\n")
        for f in file:
            plot = os.path.join(hard, f)

            print("deleting " + f + "...")

            if os.path.exists(plot):
                os.remove(plot)
                count += 1

            print("done " + f + "...\n")

            if count > n:
                print("done, deleted " + str(n) + " plots!\n")
                return

    @staticmethod
    def stop_hpool_service():
        p = subprocess.Popen("service hpoolpp stop",
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
            return True

        return False

    @staticmethod
    def start_hpool_service():
        p = subprocess.Popen("service hpoolpp start",
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
            return True

        return False

    @staticmethod
    def stop_nossd_service():
        p = subprocess.Popen("service nossd stop",
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
            return True

        return False

    @staticmethod
    def start_nossd_service():
        p = subprocess.Popen("service nossd start",
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
            return True

        return False

    def get_nossd_status(self):
        p = subprocess.Popen("service nossd status",
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
            self.nossd_status = p.stdout.readlines()

        if self.debug:
            for line in self.nossd_status:
                print(line)

    def is_nossd_farming(self):
        if not self.is_nossd_plotting() and not self.is_nossd_finalizing():
            for line in self.nossd_status:
                if "running" in line:
                    return True

        return False

    def is_nossd_plotting(self):
        for line in self.nossd_status:
            if "Plotting" in line:
                return True

        return False

    def is_nossd_finalizing(self):
        for line in self.nossd_status:
            if "Finalizing" in line:
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
        if str(drive_path) in self.tmp_drive_paths:
            d.tmp_drive_flag = True
            nossd_space -= self.total_tmp_space / self.parallel_nossd_num

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

        for drive_dir in dirs:
            drive_dir_path = self.drive_root_path / drive_dir
            drive_info = self.get_drive_info(drive_dir_path)

            if self.drive_character in drive_dir:
                self.all_dirves[drive_dir_path] = drive_info

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
        print("status: {}".format(status))
        print("drive: {}".format(d.drive_path))
        print(
            "drive info: [total_gb/used_gb/free_gb] : [{}/{}/{}]".format(d.total_gb, d.used_gb, d.free_gb))

        print("nossd dir: {}".format(d.nossd_path))
        print("nossd info: fpts_n: {} spts_n: {}".format(d.fpts_n, d.spts_n))

        print("plots dir: {}".format(d.plots_path))
        print("plots info: plots_n: {}".format(d.plots_n))

    def is_completed_drive(self, d: DriveInfo) -> bool:

        condition = d.target_fpts_n == d.fpts_n if self.fpt_priority else d.target_spts_n == d.spts_n

        if not d.plotting_flag and not d.finalizing_flag:
            if (d.plots_n == 0 and d.free_gb < self.min_free_space) or condition:
                self.print_drive_info("completed", d)
                return True

        return False

    def is_ready_drive(self, d: DriveInfo) -> bool:

        if not d.plotting_flag and not d.finalizing_flag:
            if d.spts_n == 0 and d.fpts_n == 0:
                self.print_drive_info("ready", d)
                return True

        return False

    def is_plotting_drive(self, d: DriveInfo) -> bool:

        if d.plotting_flag:
            self.print_drive_info("plotting", d)
            return True

        return False

    def is_finalizing_drive(self, d: DriveInfo) -> bool:

        if d.finalizing_flag:
            self.print_drive_info("finalizing", d)
            return True

        return False
    
    def is_tmp_drive(self, d: DriveInfo) -> bool:

        if d.tmp_drive_flag:
            self.print_drive_info("tmp_drive", d)
            return True

        return False
    
    def is_standby_drive(self, d: DriveInfo) -> bool:

        if d.tmp_drive_flag:
            self.print_drive_info("tmp_drive", d)
            return True

        return False
    
    def get_drives_status(self):

        for drive in self.all_dirves:

            drive_info = self.all_dirves[drive]

            if self.is_completed_drive(drive_info):  # 已完成磁盘
                self.readonly_drives[drive] = drive_info
            elif self.is_tmp_drive(drive_info):  # 临时文件磁盘
                self.tmp_spt_or_fpt_drives[drive] = drive_info
            else: #其余转换磁盘
                self.spt_or_fpt_drives[drive] = drive_info 
              
            if self.is_plotting_drive(drive_info):  # 正在转换spt
                self.plotting_drives[drive] = drive_info
                
            if self.is_finalizing_drive(drive_info):  # 正在转换fpt
                self.finalizing_drives[drive] = drive_info
    
    def update_nossd_start_sh(self):
        start_sh_context = '#!/usr/bin/env bash \n'\
                           'cd \"$(dirname \"$(realpath \"${BASH_SOURCE[0]:-$0}\")\")\"\n'
        start_sh_context += str(self.nossd_client_client) + " \\" + "\n"
        start_sh_context += "	" + " -a " + str(self.nossd_client_address) + " \\" + "\n"
        start_sh_context += "	" + " -c " + \
            str(self.nossd_client_type) + " -w " + str(self.nossd_client_name) + " --no-benchmark \\" + "\n"
        
        for d in self.tmp_spt_or_fpt_drives:
            drive_info = self.tmp_spt_or_fpt_drives[d]
            
            nossd_dir = drive_info.drive_path / self.nossd_dir
            if not nossd_dir.exists():
                nossd_dir.mkdir()
                
            if self.fpt_priority:
                start_sh_context += "	 -d,{:d}GB,{:d}N,tf {} \\".format(drive_info.target_use_space, drive_info.target_fpts_n, nossd_dir) + "\n"
            else:
                start_sh_context += "	 -d,{:d}GB,{:d}N,ts {} \\".format(drive_info.target_use_space, drive_info.target_spts_n, nossd_dir) + "\n"
                
        for d in self.spt_or_fpt_drives:
            drive_info = self.spt_or_fpt_drives[d]
            
            nossd_dir = drive_info.drive_path / self.nossd_dir
            if not nossd_dir.exists():
                nossd_dir.mkdir()
                
            if self.fpt_priority:
                start_sh_context += "	 -d,{:d}GB,{:d}N,f {} \\".format(drive_info.target_use_space, drive_info.target_fpts_n, nossd_dir) + "\n"
            else:
                start_sh_context += "	 -d,{:d}GB,{:d}N,s {} \\".format(drive_info.target_use_space, drive_info.target_spts_n, nossd_dir) + "\n"
                
        for d in self.readonly_drives:
            drive_info = self.readonly_drives[d]
            
            nossd_dir = drive_info.drive_path / self.nossd_dir
            if not nossd_dir.exists():
                nossd_dir.mkdir()
                
            start_sh_context += "	 -d,r {} \\".format(nossd_dir) + "\n"

        with open(self.nossd_client_start_sh, "w") as f:
            f.write(start_sh_context)
            f.close()
            
            os.chmod(self.nossd_client_start_sh, stat.S_IRWXU)

    def run(self):
        pass


if __name__ == '__main__':

    n = Hpool2Nossd()

    n.get_all_dirves()
    n.get_drives_status()
    
    n.update_nossd_start_sh()
    
    print()
