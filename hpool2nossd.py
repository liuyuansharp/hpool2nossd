import os
import subprocess
import shutil
from pathlib import Path

class Hpool2Nossd():
    def __init__(self) -> None:

        self.parallel_nossd_num = 3
        self.harvester_drives_num = 32
        self.delete_plot_per_time = 1

        self.drive_root_path = Path("/srv/")
        self.drive_character = "disk"

        self.plots_dir_name = "chiapp-files"
        self.nossd_fpt_dir_name = "nossd"

        self.nossd_client_path = "/root/install/nossd-1.2/"
        self.nossd_client_client = "/root/install/nossd-1.2/client"
        self.nossd_client_start_sh = "/root/install/nossd-1.2/start.sh"

        self.all_dirves = {}
        self.complete_drives = {}
        self.converting_drives = {}
        self.ready_drives = {}

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

    @staticmethod
    def check_nossd_service_plotting():
        p = subprocess.Popen("service nossd status",
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             encoding='utf-8'
                             )
        p.wait()

        if p.returncode == 0:
          lines = p.stdout.readlines()
          for line in lines:
            if "Plotting" in line or "Finalizing" in line:
              print(line)
              return True

        return False

    def get_drive_info(self,drive_path:Path):
        drive_info = {}

        gb = 1024 ** 3  # GB == gigabyte
        total_b, used_b, free_b = shutil.disk_usage(drive_path)

        drive_info["disk"] = [int(total_b/gb), int(used_b/gb), int(free_b/gb)]
        nossd_path = drive_path / self.nossd_fpt_dir_name
        fpts_n,spts_n = 0
        if nossd_path.exists():
          fpts_n = self.get_type_file_number(hpool_path,".fpt")
          spts_n = self.get_type_file_number(hpool_path,".spt")
        drive_info["nossd"] = [nossd_path,fpts_n,spts_n]

        hpool_path = drive_path / self.plots_dir_name
        plots_n = 0
        if hpool_path.exists():
          plots_n = self.get_type_file_number(hpool_path,".plot")
        drive_info["hpool"] = [hpool_path,plots_n]
        
        return drive_info

    def get_all_dirves(self):
        dirs = os.listdir(self.drive_root_path)

        for drive_dir in dirs:
          drive_dir_path = self.drive_root_path / drive_dir
          drive_info = self.get_drive_info(drive_dir_path)
          
          if self.drive_character in drive_dir:
            self.all_dirves[drive_dir_path]= drive_info

        return self.all_dirves

    def check_plots_exists(self,drive_dir_path):
        dirs = os.listdir(drive_dir_path)

        if self.plots_dir_name in dirs:
            return True

        return False

    def check_plots(self,dir_name):
        if self.plots_dir_name == dir_name:
          return True

        return False

    @staticmethod
    def get_type_file_number(dir,type):
        files = os.listdir(dir)
        no = 0
        for file in files:
          if type in file:
            no += 1

        return no

    def check_plots_full(self,drive,value):
        drive_dir_path = drive
        total_gb = value[0]
        used_gb = value[1]
        free_gb = value[2]

        dirs = os.listdir(drive_dir_path)

        for dir in dirs:
          if self.check_plots(dir):
            dir_path = drive_dir_path / dir
            if self.get_type_file_number(dir_path) and free_gb < 100:
                return True

        return False

    def check_plots_empty(self,drive,value):
        drive_dir_path = drive
        total_gb = value[0]
        used_gb = value[1]
        free_gb = value[2]

        if not self.check_plots_exists(drive_dir_path):
          return True

        dirs = os.listdir(drive_dir_path)
        for dir in dirs:
          if self.check_plots(dir):
            dir_path = drive_dir_path / dir
            files = os.listdir(dir_path)
            if not files:
              return True

        return False

    def check_nossd_exists(self,drive_dir_path):
        dirs = os.listdir(drive_dir_path)

        if self.nossd_fpt_dir_name in dirs:
            return True

        return False

    def check_nossd(self,dir_name):
        if self.nossd_fpt_dir_name == dir_name:
          return True

        return False

    @staticmethod
    def check_nossd_no_spt_file(dir):
        files = os.listdir(dir)
        spt_count = 0 
        for file in files:
          if "spt" in file:
            spt_count += 1
            if spt_count > 1: #允许保留一个spt文件
              return False

        return True

    def check_nossd_full(self,drive_info):
        drive_dir_path = drive_info["nossd"][0]
        fpts_n = drive_info["nossd"][1]
        spts_n = drive_info["nossd"][2]

        total_gb = drive_info["disk"][0]
        used_gb = drive_info["disk"][1]
        free_gb = drive_info["disk"][2]

        dirs = os.listdir(drive_dir_path)

        for dir in dirs:
          if self.check_nossd(dir):
            dir_path = drive_dir_path / dir
            if fpts_n and free_gb < 80:
                return True

        return False

    def check_nossd_empty(self,drive,value):
        drive_dir_path = drive
        total_gb = value[0]
        used_gb = value[1]
        free_gb = value[2]

        if not self.check_nossd_exists(drive_dir_path):
          return True

        dirs = os.listdir(drive_dir_path)

        for dir in dirs:
          if self.check_nossd(dir):
            dir_path = drive_dir_path / dir
            files = os.listdir(dir_path)
            if not files:
              return True

        return False

    def get_drives_status(self):

        for drive in self.all_dirves:
          drive_info = self.all_dirves[drive]
          if self.check_nossd_full(drive_info) and self.check_plots_empty(drive_info):
            self.complete_drives[drive] = drive_info

          if self.check_nossd_empty(drive_info):
            self.ready_drives[drive] = drive_info

          if not self.check_nossd_empty(drive_info) and not self.check_nossd_full(drive_info):
            self.converting_drives[drive] = drive_info

        converting_drives_num = len(self.converting_drives)
        if converting_drives_num != self.parallel_nossd_num:
          print("error converting drives number: {} : {}".format(converting_drives_num,self.parallel_nossd_num))
          exit(1)
        
        total_drives_number = len(self.complete_drives) + len(self.ready_drives) + len(self.converting_drives)
        if total_drives_number != self.harvester_drives_num:
          print("error total drives number: {} : {}".format(total_drives_number,self.harvester_drives_num))
          exit(1)

        common = self.complete_drives.keys() & self.ready_drives.keys() & self.converting_drives.keys()
        if common:
          print("error common in drives: {}".format(common))
          exit(1)

    @staticmethod
    def update_nossd_start_sh(start_sh,client,address,type,name,d1,d2,d3,complete_drives):
      start_sh_context = '#!/usr/bin/env bash \n'\
                         'cd \"$(dirname \"$(realpath \"${BASH_SOURCE[0]:-$0}\")\")\"\n'
      start_sh_context += str(client) + " \ \n"
      start_sh_context += "	" + " -a " + str(address) + " \ \n"
      start_sh_context += "	" + " -c " + str(type) + " -w " + str(name) + " --no-benchmark \ \n"
      start_sh_context += "	" + " -d " + str(d1) + " \ \n"
      start_sh_context += "	" + " -d " + str(d2) + " \ \n"
      start_sh_context += "	" + " -d " + str(d3) + " \ \n"

      for d in complete_drives:
        start_sh_context += "	" + " -d,r " + str(d) + " \ \n"

      
      with open(start_sh,"w") as f:
        f.write(start_sh_context)

    def run(self):
        pass


if __name__ == '__main__':
  
    n = Hpool2Nossd()

    n.get_all_dirves()
    n.get_drives_status()

    print(n.converting_drives)

    print(n.complete_drives)

    print(n.ready_drives)

    n.check_nossd_service_plotting()

    print()


