import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict


class DriveInfo():
    def __init__(self) -> None:
        self.drive_path: Path = Path()

        self.nossd_path: Path = Path()
        self.nossd_tmp_path: Path = Path()
        self.fpts_n = 0
        self.spts_n = 0

        self.plots_path: Path = Path()
        self.plots_n = 0

        self.total_gb = 0
        self.used_gb = 0
        self.free_gb = 10000000

        self.plotting_flag = False


class Hpool2Nossd():
    def __init__(self) -> None:

        self.parallel_nossd_num = 3
        self.delete_plot_per_time = 1
        self.min_free_space = 80  # gb

        self.drive_root_path = Path("/srv/")
        self.drive_character = "disk"

        self.plots_dir = "chiapp-files"
        self.nossd_dir = "nossd"

        self.nossd_client_path = Path("/root/install/nossd-1.2/")
        self.nossd_client_client = self.nossd_client_path / "client"
        self.nossd_client_start_sh = self.nossd_client_path / "start_dev.sh"
        self.nossd_tmp_file = "NoSSDChiaPool.tmp"
        self.nossd_status = ""

        self.all_dirves: Dict[Path, DriveInfo] = {}

        self.ready_drives: Dict[Path, DriveInfo] = {}
        self.plotting_drives: Dict[Path, DriveInfo] = {}
        self.standby_drives: Dict[Path, DriveInfo] = {}
        self.finished_drives: Dict[Path, DriveInfo] = {}
        self.completed_drives: Dict[Path, DriveInfo] = {}
        
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

    def is_drive_in_nossd_service(self, d: DriveInfo):
        for line in self.nossd_status:
            plotting_path = str(d.nossd_path)
            if d.nossd_path != Path() and plotting_path in line:
                return True

        return False
      
    def is_drive_rw_in_nossd_service(self, d: DriveInfo):
        for line in self.nossd_status:
            plotting_path = "-d " + str(d.nossd_path)
            if d.nossd_path != Path() and plotting_path in line:
                return True

        return False
      
    def is_drive_r_in_nossd_service(self, d: DriveInfo):
        for line in self.nossd_status:
            plotting_path = "-d,r " + str(d.nossd_path)
            if d.nossd_path != Path() and plotting_path in line:
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

            if plotting_n:
                d.plotting_flag = True
                
        d.nossd_path = nossd_path
        d.fpts_n = fpts_n
        d.spts_n = spts_n

        nossd_tmp_path = drive_path / self.nossd_dir / self.nossd_tmp_file
        if nossd_tmp_path.exists():
            d.nossd_tmp_path = nossd_tmp_path

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

    def is_completed_drives(self, d: DriveInfo) -> bool:

        if not self.is_drive_rw_in_nossd_service(d) and not d.plotting_flag:
            if d.plots_n == 0 and d.free_gb < self.min_free_space:
                self.print_drive_info("completed",d)
                return True

        return False

    def is_finished_drives(self, d: DriveInfo) -> bool:

        if self.is_drive_rw_in_nossd_service(d) and not d.plotting_flag:
            if d.free_gb < self.min_free_space:
                self.print_drive_info("finished",d)
                return True

        return False

    def is_ready_drives(self, d: DriveInfo) -> bool:

        if not self.is_drive_in_nossd_service(d) and not d.plotting_flag:
            if d.spts_n == 0 and d.fpts_n == 0:
                self.print_drive_info("ready",d)
                return True

        return False

    def is_plotting_drives(self, d: DriveInfo) -> bool:

        if self.is_drive_rw_in_nossd_service(d) and d.plotting_flag:
            self.print_drive_info("plotting",d)
            return True

        return False

    def is_standby_drives(self, d: DriveInfo) -> bool:

        if self.is_drive_rw_in_nossd_service(d) and not d.plotting_flag:
            self.print_drive_info("standby",d)
            return True

        return False

    def get_drives_status(self):

        for drive in self.all_dirves:

            drive_info = self.all_dirves[drive]

            if self.is_completed_drives(drive_info):  # 已完成磁盘
                self.completed_drives[drive] = drive_info
            elif self.is_plotting_drives(drive_info):  # 正在转换磁盘
                self.plotting_drives[drive] = drive_info
            elif self.is_standby_drives(drive_info):  # 等待转换磁盘
                self.standby_drives[drive] = drive_info
            elif self.is_finished_drives(drive_info):  # 任务完成磁盘
                self.finished_drives[drive] = drive_info
            elif self.is_ready_drives(drive_info):  # 可转换磁盘
                self.ready_drives[drive] = drive_info
            else:
                pass

        task_drives_num = len(self.plotting_drives) + \
            len(self.standby_drives) + len(self.finished_drives)
        if task_drives_num != self.parallel_nossd_num:
            print("error task drives number: {} : {}".format(
                task_drives_num, self.parallel_nossd_num))
            exit(1)

        common = self.ready_drives.keys() & self.plotting_drives.keys(
        ) & self.standby_drives.keys() & self.finished_drives.keys() & self.completed_drives.keys()
        if common:
            print("error common in drives: {}".format(common))
            exit(1)

    @staticmethod
    def update_nossd_start_sh(start_sh, client, address, type, name, d1, d2, d3, complete_drives):
        start_sh_context = '#!/usr/bin/env bash \n'\
                           'cd \"$(dirname \"$(realpath \"${BASH_SOURCE[0]:-$0}\")\")\"\n'
        start_sh_context += str(client) + " \ \n"
        start_sh_context += "	" + " -a " + str(address) + " \ \n"
        start_sh_context += "	" + " -c " + \
            str(type) + " -w " + str(name) + " --no-benchmark \ \n"
        start_sh_context += "	" + " -d " + str(d1) + " \ \n"
        start_sh_context += "	" + " -d " + str(d2) + " \ \n"
        start_sh_context += "	" + " -d " + str(d3) + " \ \n"

        for d in complete_drives:
            start_sh_context += "	" + " -d,r " + str(d) + " \ \n"

        with open(start_sh, "w") as f:
            f.write(start_sh_context)

    def run(self):
        pass


if __name__ == '__main__':

    n = Hpool2Nossd()

    n.get_all_dirves()
    n.get_nossd_status()
    n.get_drives_status()

    print()
