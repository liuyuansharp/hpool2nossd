# Hpool转Nossd自动化工具

## 特点
- 可支持自定义fpt/spt优先级
- 可支持自定义每次删除图数量
- 开机启动，无人值守
## 简介
- 完成Hpool plots 到 Nossd fpt的转换
- Nossd、Hpool、Hpool2nossd需配置成服务
- Nossd和Hpool服务调度
    - 初始状态设定
        - 1.获取初始磁盘列表
        - 2.获取初始磁盘状态
        - 3.判断当前磁盘状态
        - 4.停止Nossd服务
        - 5.初始化Nossd脚本
        - 6.启动Nossd服务
    - 已设定磁盘转换
        - 1.检测磁盘转换情况，如果Nossd转换满磁盘
        - 2.停止Hpool服务(由于Hpool minner独占磁盘,需停止后才能删除plots)
        - 3.删除一定数量的plots
        - 4.启动Hpool服务
        - 5.停止Nossd服务
        - 6.更新Nossd脚本
        - 7.启动Nossd服务
        - 8.继续检测Nossd服务,重复1-7
    - 循环监控重复 `已设定磁盘转换` 
    - 程序退出，当待转换Hpool plots磁盘全部转换完成
## 使用方法

### 获取hpool2nossd.py
```bash
#安装python3
su root
apt install python3

#下载
git clone https://github.com/liuyuansharp/hpool2nossd.git
```
### 配置hpool2nossd输入
``` python
#配置hpool2nossd.py 47-88行
###################配置区域开始###################
#是否fpt文件优先
self.fpt_priority = False
#每次删除hpool图数量
self.delete_plots_num_per_time = 2

#磁盘挂载根目录
self.drive_root_path = Path("/srv/")
#磁盘文件夹标识（用于排除磁盘挂载根目录下排除无效目录，可为填""，则不作排除）
self.drive_character = "disk"

#hpool图目录名
self.plots_dir = "chiapp-files"
#nossd图目录名
self.nossd_dir = "nossd"
#hpool服务名
self.hpool_service = "hpoolpp"
#nossd服务名
self.nossd_service = "nossd"

#nossd安装文件目录
self.nossd_path = Path("/root/install/nossd-1.2/")
#nossd脚本名
self.nossd_start_sh_name = "start.sh"

#nossd压缩等级
self.nossd_type = 5
#nossd机器名
self.nossd_name = "bsh_001"
#nossd收益地址
self.nossd_address = "xch1m49h6ny95xgs5a3p2wg6ghnr3vejsqq2pwklq9ae8kg8wgkfujcs26djuq"
#nossd临时文件磁盘
self.nossd_tmp_drive_paths = \
    [
        "/srv/dev-disk-by-uuid-9802c526-c5e2-44a4-9e29-b7e1b7b805a0",
        "/srv/dev-disk-by-uuid-ffeb0e19-8f2a-453a-abec-9aa7884c1124",
        "/srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01"
    ]
###################配置区域结束####################

```

### 配置hpool2nossd服务
```bash
# 必须是root用户
# sudo su

# 创建systemd服务，根据hpool2nossd.py位置 配置以下路径
cat > /lib/systemd/system/hpool2nossd.service <<EOF
[Unit]
Description=hpool2nossd
After=multi-user.target
StartLimitIntervalSec=0

[Service]
Type=forking
ExecStart=/bin/bash -c "/usr/bin/python3 /root/install/hpool2nossd/hpool2nossd.py &"
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Restart=always
RestartSec=1
TimeoutStartSec=30
User=root

[Install]
WantedBy=multi-user.target
EOF

# 设置开机启动
systemctl daemon-reload
systemctl enable hpool2nossd
```

### 配置hpool服务
```bash
# 必须是root用户
# sudo su

# 创建systemd服务，根据hpool minner位置 配置以下路径
cat > /lib/systemd/system/hpoolpp.service <<EOF
[Unit]
Description=hpoolpp
After=multi-user.target
StartLimitIntervalSec=0

[Service]
Type=forking
ExecStart=/bin/bash -c "/home/chiapp/linux/hpool-miner-chia-pp -config /home/chiapp/config.yaml &" 
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Restart=always
RestartSec=1
TimeoutStartSec=30
User=root

[Install]
WantedBy=multi-user.target
EOF

# 设置开机启动
systemctl daemon-reload
systemctl enable hpoolpp

```

### 配置nossd服务
```bash
# 必须是root用户
# sudo su

# 创建systemd服务，根据nossd minner位置 配置以下启动脚本路径
cat > /lib/systemd/system/nossd.service <<EOF
[Unit]
Description=nossd
After=multi-user.target
StartLimitIntervalSec=0

[Service]
Type=forking
ExecStart=/bin/bash -c "/root/install/nossd-1.2/start.sh &"  
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
Restart=always
RestartSec=1
TimeoutStartSec=30
User=root

[Install]
WantedBy=multi-user.target
EOF

# 设置开机启动
systemctl daemon-reload
systemctl enable nossd

```

### 启动并检查hpoolpp记录
```bash
#启动hpoolpp服务
systemctl start hpoolpp

#查看日志
journalctl -u hpoolpp.service -f
```

```log
1月 11 21:04:22 harvester2 bash[2342835]: time="2023-01-11T21:04:22+08:00" level=info msg="upload status" file=loggers.go func=logging.CPrint interval=180 line=168 pre upload time="2023-01-11 21:01:22" tid=21505
1月 11 21:04:24 harvester2 bash[2342835]: time="2023-01-11T21:04:24+08:00" level=info msg="new mining info" capacity="254.59 TB" chain=Chia file=loggers.go func=logging.CPrint height=3091271 jobId=942747955 line=168 scan consume=4416 scan time="2023-01-11 21:04:16" tid>
1月 11 21:04:33 harvester2 bash[2342835]: time="2023-01-11T21:04:33+08:00" level=info msg="new mining info" capacity="254.59 TB" chain=Chia file=loggers.go func=logging.CPrint height=3091271 jobId=892613170 line=168 scan consume=4416 scan time="2023-01-11 21:04:24" tid>
1月 11 21:04:43 harvester2 bash[2342835]: time="2023-01-11T21:04:43+08:00" level=info msg="new mining info" capacity="254.59 TB" chain=Chia file=loggers.go func=logging.CPrint height=3091271 jobId=1630955058 line=168 scan consume=4416 scan time="2023-01-11 21:04:33" ti>
1月 11 21:04:52 harvester2 bash[2342835]: time="2023-01-11T21:04:52+08:00" level=info msg="new mining info" capacity="254.59 TB" chain=Chia file=loggers.go func=logging.CPrint height=3091272 jobId=1633890352 line=168 scan consume=4416 scan time="2023-01-11 21:04:43" ti>
1月 11 21:05:01 harvester2 bash[2342835]: time="2023-01-11T21:05:01+08:00" level=info msg="new mining info" capacity="254.59 TB" chain=Chia file=loggers.go func=logging.CPrint height=3091272 jobId=892613218 line=168 scan consume=4416 scan time="2023-01-11 21:04:52" tid>
1月 11 21:05:11 harvester2 bash[2342835]: time="2023-01-11T21:05:11+08:00" level=info msg="new mining info" capacity="254.59 TB" chain=Chia file=loggers.go func=logging.CPrint height=3091272 jobId=828519523 line=168 scan consume=4416 scan time="2023-01-11 21:05:01" tid>
```

### 启动并检查nossd记录
```bash
#启动nossd服务
systemctl start nossd

#查看日志
journalctl -u nossd.service -f
```

```log
1月 11 21:03:39 harvester2 bash[2342868]: 21:03:39 Signage point 6c42...c2b0
1月 11 21:03:41 harvester2 bash[2342868]: 21:03:41 Plotting, 53%, 53m 17s elapsed, 46m 40s remaining
1月 11 21:03:49 harvester2 bash[2342868]: 21:03:49 Signage point 08c6...5ec3
1月 11 21:03:51 harvester2 bash[2342868]: 21:03:51 Plotting, 54%, 53m 27s elapsed, 46m 30s remaining
1月 11 21:03:51 harvester2 bash[2342868]: 21:03:51 Share generated using plot a420...b50c
1月 11 21:03:57 harvester2 bash[2342868]: 21:03:57 Signage point 2e05...5003
1月 11 21:04:01 harvester2 bash[2342868]: 21:04:01 Plotting, 54%, 53m 37s elapsed, 46m 11s remaining
1月 11 21:04:06 harvester2 bash[2342868]: 21:04:06 Signage point 1584...e690
1月 11 21:04:11 harvester2 bash[2342868]: 21:04:11 Plotting, 54%, 53m 47s elapsed, 45m 52s remaining
1月 11 21:04:16 harvester2 bash[2342868]: 21:04:16 Signage point 69c5...bd9e
```


### 启动并检查hpool2nossd记录
```bash
#启动hpool2nossd服务
systemctl start hpool2nossd

#查看日志
journalctl -u hpool2nossd.service -f
```

```log
1月 11 20:05:03 harvester2 bash[2342018]: waitting 300 s ,check drives status again....
1月 11 20:10:03 harvester2 bash[2342018]: check drives status....
1月 11 20:10:17 harvester2 bash[2342018]: deleting /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files/plot-k32-2022-03-27-00-54-977cdabd25fe149603ef12743de23fdd5680f374ac21904219d2e4401adeae3b.plot...
1月 11 20:10:17 harvester2 bash[2342018]: done /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files/plot-k32-2022-03-27-00-54-977cdabd25fe149603ef12743de23fdd5680f374ac21904219d2e4401adeae3b.plot...
1月 11 20:10:17 harvester2 bash[2342018]: deleting /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files/plot-k32-2022-03-27-07-50-7f5b8e9210de29bef6741f1205d2e385969d37adc8a793e0b238dd9518191457.plot...
1月 11 20:10:17 harvester2 bash[2342018]: done /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files/plot-k32-2022-03-27-07-50-7f5b8e9210de29bef6741f1205d2e385969d37adc8a793e0b238dd9518191457.plot...
1月 11 20:10:17 harvester2 bash[2342018]: done, deleted 2 plots in /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files!
1月 11 20:10:17 harvester2 bash[2342018]: status: deleted
1月 11 20:10:17 harvester2 bash[2342018]: drive: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01
1月 11 20:10:17 harvester2 bash[2342018]: drive info: [total_gb/used_gb/free_gb] : [16696/16681/14]
1月 11 20:10:17 harvester2 bash[2342018]: nossd dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/nossd
1月 11 20:10:17 harvester2 bash[2342018]: nossd info: fpts_n: 77 spts_n: 11
1月 11 20:10:17 harvester2 bash[2342018]: plots dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files
1月 11 20:10:17 harvester2 bash[2342018]: plots info: plots_n: 93
1月 11 20:10:19 harvester2 bash[2342018]: waitting 300 s ,check drives status again....
1月 11 20:15:20 harvester2 bash[2342018]: check drives status....
1月 11 20:15:21 harvester2 bash[2342018]: status: plotting
1月 11 20:15:21 harvester2 bash[2342018]: drive: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01
1月 11 20:15:21 harvester2 bash[2342018]: drive info: [total_gb/used_gb/free_gb] : [16696/16478/217]
1月 11 20:15:21 harvester2 bash[2342018]: nossd dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/nossd
1月 11 20:15:21 harvester2 bash[2342018]: nossd info: fpts_n: 77 spts_n: 12
1月 11 20:15:21 harvester2 bash[2342018]: plots dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files
1月 11 20:15:21 harvester2 bash[2342018]: plots info: plots_n: 93
1月 11 20:15:21 harvester2 bash[2342018]: waitting 300 s ,check drives status again....
1月 11 20:20:21 harvester2 bash[2342018]: check drives status....
1月 11 20:20:21 harvester2 bash[2342018]: status: plotting
1月 11 20:20:21 harvester2 bash[2342018]: drive: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01
1月 11 20:20:21 harvester2 bash[2342018]: drive info: [total_gb/used_gb/free_gb] : [16696/16478/217]
1月 11 20:20:21 harvester2 bash[2342018]: nossd dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/nossd
1月 11 20:20:21 harvester2 bash[2342018]: nossd info: fpts_n: 77 spts_n: 12
1月 11 20:20:21 harvester2 bash[2342018]: plots dir: /srv/dev-disk-by-uuid-0ee42af9-6cc1-41a3-992c-c7a80a764b01/chiapp-files
1月 11 20:20:21 harvester2 bash[2342018]: plots info: plots_n: 93
1月 11 20:20:21 harvester2 bash[2342018]: waitting 300 s ,check drives status again....
```